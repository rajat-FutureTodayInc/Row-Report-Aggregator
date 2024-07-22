#!/usr/bin/env python
# coding: utf-8

# In[1]:


import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import io
from io import BytesIO


#Function that Aggregates the node level data on the basis of L1, PlayListId and ActionPlayListId(this function is used in the actual function that generates all the Nodes within a PlayList)
def Node_inside_PlayList(raw_data, L1, Play_list_id, Action_PlayListID):
    data = raw_data.copy()

    #The rows for which completion% is null have been removed
    data = data.dropna(subset = ['Completion Percent'])

    #masking tha data on the basis of L1, PlayListId and ActionPlayListId given
    mask1 = (data['L1 Category'] == L1) | (L1 == "All")
    mask2 = (data['Play ListID'] == Play_list_id) | (Play_list_id == "All")
    data1 = data[mask1 & mask2]
    mask3 = (data1['Action PlayListID'] == Action_PlayListID) | (Action_PlayListID == 'All')
    data1 = data1[mask3]  
    
    data1 = data1.assign(Node_Watch_Time = (data1['Node Watch Time'] / 3600))  # converting watch time from sec to hrs


    #Columns used for grouping to aggregate the data
    index_columns = ['L1 Category', 'Play ListID', 'Action PlayListID', 'Node Id', 'Node Title']

    #If any of the columns are All then they are removed as they are not used for grouping
    if L1 == 'All':
        index_columns.remove('L1 Category')
    if Play_list_id == 'All':
        index_columns.remove('Play ListID')
    if Action_PlayListID == 'All':
        index_columns.remove('Action PlayListID')

    #Aggerating the node data on the basis of index columns
    piv_data = pd.pivot_table(data1, values=['Node Views', 'Node_Watch_Time', 'Completion Percent', 'Node Unique Users'], index=index_columns, aggfunc={'Node Views':'sum', 'Node_Watch_Time':'sum', 'Completion Percent':'mean', 'Node Unique Users':'sum'})
    
    #Returning if the pivot table is empty
    if piv_data.shape[0] == 0:
        return piv_data


    #FUNCTION TO GENERATE THE LATEST POSITION FOR EACH NODE
    data2 = data1.copy()
    data3 = data2.iloc[:, [22, 24]].dropna(subset=['Node Id']).drop_duplicates(subset=['Node Id'])      #extracting the node id and node position column and taking only unique node
    
    #Assigning the node position to each node 
    data3['Node Position'] = np.nan

    #iterating over each node id and extracting the position corresponding to the latest date from the raw_data 
    for i in range(data3.shape[0]):
        node_id = data3['Node Id'].iloc[i]
        df1 = data2[data2['Node Id'] == node_id].sort_values(by='Date', ascending=False).reset_index()
        data3.loc[data3['Node Id'] == node_id, 'Node Position'] = df1['Node Position'].iloc[0]


    #Assigning the AWD
    piv_data = piv_data.assign(awd=np.where(piv_data['Node Views'] == 0, np.nan, (piv_data['Node_Watch_Time'] / piv_data['Node Views']) * 60))


    #Merging the latest position column for each node id with the pivot table
    df = pd.merge(piv_data.reset_index(), data3, on='Node Id', how='left')
    
    #Adding the names of the PlayList and ActionPlaylist by mapping them to their ids
    if 'Play ListID' in df.columns:
        play_list_dict = data1.set_index('Play ListID')['Play List'].to_dict()
        df = df.assign(Play_List=df['Play ListID'].map(play_list_dict))
        cols = list(df.columns)
        cols.insert(df.shape[1] - 10, cols.pop(cols.index('Play_List')))
        df = df[cols]
    
    if 'Action PlayListID' in df.columns:
        actionplay_list_dict = data1.set_index('Action PlayListID')['Action PlayList'].to_dict()
        df = df.assign(ActionPlay_List=df['Action PlayListID'].map(actionplay_list_dict))  
        cols = list(df.columns)
        cols.insert(df.shape[1] - 9, cols.pop(cols.index('ActionPlay_List')))
        df = df[cols]    


    df.sort_values(by = 'Node_Watch_Time', ascending = False, inplace = True)
    
    return df


#The function that aggregates the Node data on the basis of L1 and PlayList Id and returns the data in the excel file
def Node_within_PlayList(raw_data, L1, Play_list_id):
    data = raw_data.copy()

    #masking the data w.r.t to L1 and PlaylistId
    mask1 = (data['L1 Category'] == L1) | (L1 == 'All')
    mask2 = (data['Play ListID'] == Play_list_id) | (Play_list_id == 'All')
    data1 = data[mask1 & mask2]

    #Generating Unique ActionPlayListIds present in the given PlaylistId 
    data2 = data1.copy()
    data3 = data2.iloc[:, [14, 15]].copy()
    data3 = data3.dropna(subset=['Action PlayListID']).drop_duplicates(subset=['Action PlayListID']).reset_index(drop=True)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        #Iterating over each ActionPlayListId and generating the aggregated data
        for index, row in data3.iterrows():
            pvt = Node_inside_PlayList(data1, L1, Play_list_id, row['Action PlayListID'])
            sheet_name = f'Id {row["Action PlayListID"]}'                         #storing each aggregated data for a ActionPlaylistId in different sheets
            pvt.to_excel(writer, sheet_name=sheet_name, index=True)
    output.seek(0)
    return output


#Function to generate the aggregated data when user wants to upload a raw_input excel file (Stores the output excel file for each PlaylistId in the zip folder)
def Node_in_PlayList(raw_data, raw_input):
    with io.BytesIO() as buffer:
        with zipfile.ZipFile(buffer, 'w') as zipf:
            for index, row in raw_input.iterrows():
                excel_data = Node_within_PlayList(raw_data, row['L1 Category'], row['Play ListID'])
                zipf.writestr(f'{row["Play ListID"]}.xlsx', excel_data.getvalue())
        buffer.seek(0)
        return buffer.getvalue()

#Main function that creates a streamlit App that aggregate the Node data on the basis of PlayList
def main():
    # Streamlit app
    st.title("Node within PlayList Analyzer")

    uploaded_file = st.file_uploader("Choose a raw data file", type=["csv", "xlsx"])

    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            raw_data = pd.read_csv(uploaded_file)
        else:
            raw_data = pd.read_excel(uploaded_file)

        use_raw_input = st.radio("Do you want to import a raw input file?", ('No', 'Yes'))

        raw_data.drop_duplicates(inplace=True)

        raw_data['Date'] = pd.to_datetime(raw_data['Date'], format='%B %d, %Y')
        
        if use_raw_input == 'Yes':
            uploaded_input_file = st.file_uploader("Choose a raw input file", type=["csv", "xlsx"])

            if uploaded_input_file and st.button("Run Analysis with Input File"):
                if uploaded_input_file.name.endswith('.csv'):
                    raw_input = pd.read_csv(uploaded_input_file)
                else:
                    raw_input = pd.read_excel(uploaded_input_file)

                output_zip = Node_in_PlayList(raw_data, raw_input)
                st.download_button(
                    label="Download Output Zip File",
                    data=output_zip,
                    file_name="output.zip",
                    mime="application/zip"
                )
        else:
            L1_categories = ["All"] + raw_data['L1 Category'].unique().tolist()
            L1_selected = st.selectbox("Select L1 Category", L1_categories)

            if L1_selected == "All":
                Play_ListID = ["All"] + raw_data['Play ListID'].dropna().unique().tolist()
            else:
                Play_ListID = ["All"] + raw_data[raw_data['L1 Category'] == L1_selected]['Play ListID'].dropna().unique().tolist()

            Play_ListID_selected = st.selectbox("Select Play ListID", Play_ListID)

            if st.button("Run Analysis"):
                output_excel = Node_within_PlayList(raw_data, L1_selected, Play_ListID_selected)
                st.download_button(
                    label="Download Output Excel File",
                    data=output_excel,
                    file_name="output.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.warning("Please upload a raw data file to proceed.")


    # In[ ]:




