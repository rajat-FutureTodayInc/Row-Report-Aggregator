#!/usr/bin/env python
# coding: utf-8

# In[1]:


import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

def Node_within_ActionPlayList(raw_data, L1, L2, Action_PlayListID):
    data1 = raw_data.copy()
    
    data = data1.assign(Node_Watch_time_hr=data1['Node Watch Time'] / 3600)
    data = data.dropna(subset = ['Completion Percent'])
    
    # Apply filters
    if L1 != "All":
        data = data[data['L1 Category'] == L1]
    if L2 != "All":
        data = data[data['L2 Category'] == L2]
    if Action_PlayListID != "All":
        data = data[data['Action PlayListID'] == Action_PlayListID]
    
    # Copy the filtered data
    data2 = data.copy()
    
    # Select specific columns and handle missing values
    data3 = data2.iloc[:, [22, 24]].dropna(subset=['Node Id']).drop_duplicates(subset=['Node Id'])
    
    # Initialize Node Position column
    data3['Node Position'] = np.nan
    
    # Populate Node Position based on the sorted data
    for i in range(data3.shape[0]):
        node_id = data3['Node Id'].iloc[i]
        df1 = data2[data2['Node Id'] == node_id].sort_values(by='Date',ascending = False).reset_index()
        data3.loc[data3['Node Id'] == node_id, 'Node Position'] = df1['Node Position'].iloc[0]
    
    index_columns = ['L1 Category','L2 Category','Action PlayListID','Node Id', 'Node Title']

    # Remove columns from index based on conditions
    if L1 == 'All':
        index_columns.remove('L1 Category')
    if L2 == 'All':
        index_columns.remove('L2 Category')
    if Action_PlayListID == 'All':
        index_columns.remove('Action PlayListID')
    
    # Create a pivot table    
    piv_data = pd.pivot_table(
        data, 
        values=['Node Views', 'Completion Percent', 'Node_Watch_time_hr'],
        index=index_columns,
        aggfunc={
            'Node Views': 'sum',
            'Completion Percent': 'mean',
            'Node_Watch_time_hr': 'sum'
        }
    )
    
    if(piv_data.shape[0] == 0):
        return piv_data
    
        
    piv_data = piv_data.assign(wt_view = np.where(piv_data['Node Views'] == 0, np.nan, (piv_data['Node_Watch_time_hr'] / piv_data['Node Views'])*60))

    
    # Merge the pivot table with data3
    df = pd.merge(piv_data.reset_index(), data3, on='Node Id', how='left')
    
    if('Action PlayListID' in df.columns):
        #setting the name of actionPlayList corresponding to actionPlayListId
        actionplay_list_dict = data.set_index('Action PlayListID')['Action PlayList'].to_dict()
        df = df.assign(ActionPlay_List = df['Action PlayListID'].map(actionplay_list_dict))  
        cols = list(df.columns)
        cols.insert(piv_data.shape[1]-11, cols.pop(cols.index('ActionPlay_List')))
        df = df[cols]
    
    return df


def Node_in_ActionPlayList(raw_data, raw_input):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for index, row in raw_input.iterrows():
            pvt = Node_within_ActionPlayList(raw_data, row['L1 Category'], row['L2 Category'], row['Action PlayListID'])
            idx = row['Action PlayListID']
            sheet_name = f'Id {idx}'
            pvt.to_excel(writer, sheet_name=sheet_name, index=True)
            
    output.seek(0)
    return output

def main():
    # Streamlit app
    st.title("Node within ActionPlayList Analyzer")

    # Step 1: Upload raw data file
    uploaded_file = st.file_uploader("Upload raw data file", type=["csv", "xlsx"])

    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            raw_data = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            raw_data = pd.read_excel(uploaded_file)
        
        raw_data.drop_duplicates(inplace=True)

        raw_data['Date'] = pd.to_datetime(raw_data['Date'], format='%B %d, %Y')

        
        # Radio button to choose between manual selection or file upload
        use_raw_input = st.radio(
            "Do you want to import a raw input file?",
            ('No', 'Yes')
        )

        if use_raw_input == 'Yes':
            uploaded_input_file = st.file_uploader("Choose a raw input file", type=["csv", "xlsx"])

            if uploaded_input_file and st.button("Run Analysis with Input File"):
                # Read the raw input file
                if uploaded_input_file.name.endswith('.csv'):
                    raw_input = pd.read_csv(uploaded_input_file)
                else:
                    raw_input = pd.read_excel(uploaded_input_file)

                output = Node_in_ActionPlayList(raw_data, raw_input)
                st.download_button(
                    label="Download Output Excel File",
                    data=output,
                    file_name="output.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        else:
            # Step 2: Select L1 Category
            L1_options = ["All"] + raw_data['L1 Category'].dropna().unique().tolist()
            selected_L1 = st.selectbox("Select L1 Category", L1_options)

            # Step 3: Select L2 Category
            if selected_L1 == "All":
                L2_options = ["All"] + raw_data['L2 Category'].dropna().unique().tolist()
            else:
                L2_options = ["All"] + raw_data[raw_data['L1 Category'] == selected_L1]['L2 Category'].dropna().unique().tolist()
            selected_L2 = st.selectbox("Select L2 Category", L2_options)

            # Step 4: Select ActionPlayListID
            if selected_L2 == "All":
                if selected_L1 == "All":
                    ActionPlayListID_options = ["All"] + raw_data['Action PlayListID'].dropna().unique().tolist()
                else:
                    ActionPlayListID_options = ["All"] + raw_data[raw_data['L1 Category'] == selected_L1]['Action PlayListID'].dropna().unique().tolist()
            else:
                ActionPlayListID_options = ["All"] + raw_data[raw_data['L2 Category'] == selected_L2]['Action PlayListID'].dropna().unique().tolist()
            selected_ActionPlayListID = st.selectbox("Select Action PlayList ID", ActionPlayListID_options)

            if st.button("Run Analysis"):
                # Run the aggregation function
                result = Node_within_ActionPlayList(raw_data, selected_L1, selected_L2, selected_ActionPlayListID)

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
        st.write("Please upload a raw data file.")


    # In[ ]:




