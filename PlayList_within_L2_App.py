#!/usr/bin/env python
# coding: utf-8

# In[1]:


import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# Define the PlayList_within_L2 function
def PlayList_within_L2(raw_data, L1, L2):
    data = raw_data.copy()
    data = data.iloc[:, :21]  # Removing the Node related columns as they generate duplicates

    #Applying Filters
    mask1 = (data['L1 Category'] == L1) | (L1 == "All")
    mask2 = (data['L2 Category'] == L2) | (L2 == "All")
    data1 = data[mask1 & mask2]


    #Generating the latest position columns corresponding to given PlayLists
    data2 = data1.copy()
    data3 = data2.iloc[:, [11, 13]]         #not droping the mlp column, hence 11 and 13 (if dropped 5, 7)
    data3 = data3.dropna(subset=['Play ListID'])
    data3 = data3.drop_duplicates(subset=['Play ListID']).reset_index(drop=True)

    data3['Play List Position'] = np.nan
    
    for i in range(data3.shape[0]):
        play_list_id = data3.at[i, 'Play ListID']
        df1 = data2[data2['Play ListID'] == play_list_id].sort_values(by='Date', ascending=False).reset_index()
        data3.at[i, 'Play List Position'] = df1.at[0, 'Play List Position']


    #Converting watch time from sec to hrs
    data1 = data1.assign(Watch_Time = (data1['Watch Time']/3600))

    #Removing duplicates generated due to node related columns 
    data1 = data1.drop_duplicates()     

    #Modifying the indexes on which grouping is to be done
    index_columns = ['L1 Category', 'L2 Category', 'Play ListID']
    if L1 == 'All':
        index_columns.remove('L1 Category')
    if L2 == 'All':
        index_columns.remove('L2 Category')


    #Creating the required pivot table
    piv_data = pd.pivot_table(
        data1,
        values=['Unique Users', 'Watch_Time', 'Views'],
        index=index_columns,
        aggfunc={'Unique Users': 'sum', 'Watch_Time': 'sum', 'Views':'sum'}
    )

    #Handling the case for empty pivot table
    if(piv_data.shape[0] == 0):
        return piv_data


    #Adding the PlayList names column corresponding to the PlayListId
    play_list_dict = data1.drop_duplicates(subset = ['Play ListID']).set_index('Play ListID')['Play List'].to_dict()
    piv_data = piv_data.reset_index()
    piv_data = piv_data.assign(Play_List = piv_data['Play ListID'].map(play_list_dict))  
    cols = list(piv_data.columns)
    cols.insert(piv_data.shape[1]-4, cols.pop(cols.index('Play_List')))
    piv_data = piv_data[cols]


    #Assigning wt/uu
    piv_data = piv_data.assign(wt_uu=(piv_data['Watch_Time'] / piv_data['Unique Users']) * 60)
    piv_data_reset = piv_data.reset_index()

    #Merging the latest position dataframe
    df = pd.merge(piv_data_reset, data3, on='Play ListID', how='left')
    
    df.drop(columns=['index'], inplace=True)

    df.sort_values(by = 'Watch_Time', ascending = False, inplace = True)
    
    return df

#Function that returns an aggregated output excel file when user gives a raw_input excel file instead of manually selecting the categories
def PlayList_in_L2(raw_data, raw_input):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for index, row in raw_input.iterrows():
            pvt = PlayList_within_L2(raw_data, row['L1 Category'], row['L2 Category'])
            sheet_name = row['L2 Category']
            pvt.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output


#Main function that generated a streamlit app that aggregates the PlayList data within a L2
def main():
    # Streamlit app
    st.title("PlayList Aggregator")

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
        
        raw_data.drop_duplicates(inplace=True)

        raw_data['Date'] = pd.to_datetime(raw_data['Date'], format='%B %d, %Y')

        if use_raw_input == 'Yes':
            uploaded_input_file = st.file_uploader("Choose a raw input file", type=["csv", "xlsx"])

            if uploaded_input_file and st.button("Run Analysis with Input File"):
                # Read the raw input file
                if uploaded_input_file.name.endswith('.csv'):
                    raw_input = pd.read_csv(uploaded_input_file)
                else:
                    raw_input = pd.read_excel(uploaded_input_file)

                output = PlayList_in_L2(raw_data, raw_input)
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

            # Get unique L2 categories based on selected L1
            if L1_selected == "All":
                L2_categories = ["All"] + raw_data['L2 Category'].unique().tolist()
            else:
                L2_categories = ["All"] + raw_data[raw_data['L1 Category'] == L1_selected]['L2 Category'].unique().tolist()

            # Select L2 category
            L2_selected = st.selectbox("Select L2 Category", L2_categories)

            if st.button("Run Analysis"):
                # Run the aggregation function
                result = PlayList_within_L2(raw_data, L1_selected, L2_selected)

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




