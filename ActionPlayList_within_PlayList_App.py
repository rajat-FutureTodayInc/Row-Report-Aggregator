#!/usr/bin/env python
# coding: utf-8

# In[1]:


import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO


#Fucntion that aggreagtes All the ActionPlayList in a given PlayList and returns an aggregated dataframe
def ActionPlayList_within_PlayList(raw_data, L1, Play_ListID):
    data1 = raw_data.copy()
    data1 = data1.iloc[:, 0:21]             #removing the node-related columns as they generate duplicates


    #masking the data on the basis of L1 Category and the PlayListID
    mask1 = (data1['L1 Category'] == L1) | (L1 == "All")
    mask2 = (data1['Play ListID'] == Play_ListID) | (Play_ListID == "All")
    data = data1[mask1 & mask2].copy()

    #removing the duplicated generated due to the node-related columns
    data = data.drop_duplicates()


    #FUNCTION TO GENERATE THE LATEST DATE FOR ALL THE ACTIONPLAYLISTS
    data2 = data.copy()
    data3 = data2.iloc[:, [14, 16]].copy()        #extracting the ActionPlayListId and positions from the data
    data3 = data3.dropna(subset=['Action PlayListID'])                   
    data3 = data3.drop_duplicates(subset=['Action PlayListID']).reset_index(drop=True)    #generating all the unique ActionPlayLitsIds for the given PlayListId
    
    #Assigning the ActionPlayList Position to each ActionPlayListId
    data3['Action PlayList Position'] = np.nan 
    #iterating over each ActionPlayListId and extracting the latest position for that Id
    for i in range(data3.shape[0]):
        df1 = data2[data2['Action PlayListID'] == data3.loc[i, 'Action PlayListID']].sort_values(by='Date', ascending=False)    #for the given ActionPlayListId sorting the ActionPlayList Position column according to the latest date
        data3.loc[i, 'Action PlayList Position'] = df1.reset_index().loc[0, 'Action PlayList Position']                   #extracting the first latest position of the sorted columns


    #Converting the Watch time from sec to hrs
    data = data.assign(Watch_Time=(data['Watch Time'] / 3600))
    

    #the columns on the basis of which the data will be grouped
    index_columns = ['L1 Category', 'Play ListID', 'Action PlayListID']

    # Remove columns from index based on conditions(if any of these columns are All then we need to remove them as we don't need to group on the basis of that column)
    if L1 == 'All':
        index_columns.remove('L1 Category')
    if Play_ListID == 'All':
        index_columns.remove('Play ListID')

    #Creating the required pivot table that aggregates the ActionPlayList Id data
    piv_data = pd.pivot_table(
        data,
        values=['Views', 'Watch_Time', 'Unique Users'],
        index=index_columns,
        aggfunc={'Views': 'sum', 'Watch_Time': 'sum', 'Unique Users': 'sum'}
    )

    #Returning if the pivot table is empty
    if piv_data.shape[0] == 0:
        return piv_data
    
    
    #setting the name of actionPlayList corresponding to actionPlayListId(some ActionPlayList names can be null hence the names are not included in the pivot table index rather they are added after creating the table)
    actionplay_list_dict = data.drop_duplicates(subset = ['Action PlayListID']).set_index('Action PlayListID')['Action PlayList'].to_dict() #creating a dictionary of raw data that maps all the ActionPlayListId with their names
    piv_data = piv_data.reset_index()
    piv_data = piv_data.assign(ActionPlay_List = piv_data['Action PlayListID'].map(actionplay_list_dict))   #Assinging the names for all the ActionPlayListIds present in the pivot table  
    cols = list(piv_data.columns)
    cols.insert(piv_data.shape[1]-4, cols.pop(cols.index('ActionPlay_List')))     #placing the ActionPlayList names next to their ids
    piv_data = piv_data[cols]

    #Assigning AWD for the pivot table
    piv_data = piv_data.assign(awd=np.where(piv_data['Views'] == 0, np.nan, (piv_data['Watch_Time'] / piv_data['Unique Users']) * 60))
    
    piv_data_reset = piv_data.reset_index()

    #Merging the latest position column with the pivot table
    df = pd.merge(piv_data_reset, data3, on='Action PlayListID', how='left')
    
    if('Play ListID' in df.columns):
        #setting the name of playList corresponding to PlayListId
        play_list_dict = data.set_index('Play ListID')['Play List'].to_dict()
        #piv_data = piv_data.reset_index()
        df = df.assign(Play_List = df['Play ListID'].map(play_list_dict))  
        cols = list(df.columns)
        cols.insert(df.shape[1]-8, cols.pop(cols.index('Play_List')))
        df = df[cols]
    
    #droping the unnecessary columns if present
    drop_columns = ['index', 'level_0']

    if ('index' not in df.columns):
        drop_columns.remove('index')
    if ('level_0' not in df.columns):
        drop_columns.remove('level_0')
    
    df.drop(columns=drop_columns, inplace=True)
    df.sort_values(by = 'Watch_Time', ascending = False, inplace = True)
    df['Watch_Time] = df['Watch_Time'].round(1)
    df['awd'] = df['awd'].round(1)
    
    return df


#Function that generates the aggregated data excel file if the user wants to give raw_input excel file instead of giving the input manually
def ActionPlayList_in_PlayList(raw_data, raw_input):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for index, row in raw_input.iterrows():
            pvt = ActionPlayList_within_PlayList(raw_data, row['L1 Category'], row['Play ListID'])
            idx = row['Play ListID']
            sheet_name = f'Id {idx}'
            pvt.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output


#The main function that make a streamlit app for aggregating the ActionPlayList
def main():
    # Streamlit app
    st.title("ActionPlayList Aggregator")

    # File upload
    uploaded_file = st.file_uploader("Choose a raw data file", type=["csv", "xlsx"])

    if uploaded_file:
        # Read the raw data file
        if uploaded_file.name.endswith('.csv'):
            raw_data = pd.read_csv(uploaded_file)
        else:
            raw_data = pd.read_excel(uploaded_file)

        # Radio button to choose between manual selection or file upload
        use_raw_input = st.radio(
            "Do you want to import a raw input file?",
            ('No', 'Yes')
        )
        
        raw_data.drop_duplicates(inplace = True)
        raw_data['Date'] = pd.to_datetime(raw_data['Date'], format='%B %d, %Y')
        
        if use_raw_input == 'Yes':
            uploaded_input_file = st.file_uploader("Choose a raw input file", type=["csv", "xlsx"])

            if uploaded_input_file and st.button("Run Analysis with Input File"):
                # Read the raw input file
                if uploaded_input_file.name.endswith('.csv'):
                    raw_input = pd.read_csv(uploaded_input_file)
                else:
                    raw_input = pd.read_excel(uploaded_input_file)

                output = ActionPlayList_in_PlayList(raw_data, raw_input)
                st.download_button(
                    label="Download Output Excel File",
                    data=output,
                    file_name="output.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            # Get unique L1 categories
            L1_categories = ["All"] + raw_data['L1 Category'].unique().tolist()

            # Select L1 category
            L1_selected = st.selectbox("Select L1 Category", L1_categories)

            # Get unique PlayListIds based on selected L1
            if L1_selected == "All":
                Play_ListID = ["All"] + raw_data['Play ListID'].unique().tolist()
            else:
                Play_ListID = ["All"] + raw_data[raw_data['L1 Category'] == L1_selected]['Play ListID'].unique().tolist()

            # Select PlayListId
            Play_ListID_selected = st.selectbox("Select Play ListID", Play_ListID)

            if st.button("Run Analysis"):
                # Run the aggregation function
                result = ActionPlayList_within_PlayList(raw_data, L1_selected, Play_ListID_selected)

                # Display the result
                st.write("Aggregated Data:")
                st.dataframe(result)

                # Convert dataframe to Excel for download
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    result.to_excel(writer, index=False, sheet_name="Aggregated Data")
                output.seek(0)

                st.download_button(
                    label="Download Output Excel File",
                    data=output,
                    file_name="aggregated_output.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    else:
        st.warning("Please upload a raw data file to proceed.")


    # In[ ]:




