import streamlit as st
import pandas as pd
import numpy as np
import io


#Function that returns an aggregated dataframe having all the L2s within L1
def L2_within_L1(raw_data, L1):
    data1 = raw_data.copy()
    data1 = data1.iloc[:, 0:21]     #removing the node-related columns as they generate duplicates


    #masking the data on the basis of given L1 Category
    mask1 = (data1['L1 Category'] == L1) | (L1 == "All")
    data = data1[mask1].copy()

    #removing the duplicates that were present due to the node columns
    data = data.drop_duplicates()


    #PROCESS TO EXTRACT THE LATEST POSITION FOR ALL THE L2s
    data2 = data.copy()
    data3 = data2.iloc[:, [3,4]].copy()            #extracting the L2 Categories
    data3 = data3.dropna(subset=['L2 Category'])   
    data3 = data3.drop_duplicates(subset=['L2 Category']).reset_index(drop=True)     #data3 contains all the unique L2 Categories present in a given L1 
    
    #Assigning of the latest position to all the extracted unique L2s
    data3['L2 Position'] = np.nan  
    for i in range(data3.shape[0]):        #iterating the row-report for all the unique L2s and extracting the latest date for the L2
        df1 = data2[data2['L2 Category'] == data3.loc[i, 'L2 Category']].sort_values(by='Date', ascending=False)            
        data3.loc[i, 'L2 Position'] = df1.reset_index().loc[0, 'L2 Position']             #taking the first date of the sorted date column

    #converting watch time to hrs from sec
    data = data.assign(Watch_Time=(data['Watch Time'] / 3600))              


    #making the requires pivot table
    piv_data = pd.pivot_table(
        data,
        values=['Views', 'Watch_Time', 'Unique Users'],
        index=['L1 Category','L2 Category'],
        aggfunc={'Views': 'sum', 'Watch_Time': 'sum', 'Unique Users':'sum'}
     )


    #pivot table for the case when all the L1s are selected
    if(L1 == 'All'):
        piv_data = pd.pivot_table(
            data,
            values=['Views', 'Watch_Time', 'Unique Users'],
            index=['L2 Category'],        #removing the L1 from the grouping
            aggfunc={'Views': 'sum', 'Watch_Time': 'sum', 'Unique Users':'sum'}
         )

    #handling the case when the pivot table is empty
    if(piv_data.shape[0] == 0):
        return piv_data

    #Assigning Unique Users
    piv_data = piv_data.assign(awd=np.where(piv_data['Unique Users'] == 0, np.nan, (piv_data['Watch_Time'] / piv_data['Unique Users']) * 60))
    
    piv_data_reset = piv_data.reset_index()

    #merging the date column with the pivot table created so that we can have the latest date for all L2s
    df = pd.merge(piv_data_reset, data3, on='L2 Category', how='left')

    df.sort_values(by = 'Watch_Time', ascending = False, inplace = True)
    
    return df


#Function for the case when the user wants to upload a raw-input-excel file instead of giving the input manually to the function
def L2_in_L1(raw_data, raw_input):
    output = io.BytesIO()        #output excel file
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        #iterates over each row present in the raw_input file
        for index, row in raw_input.iterrows():
            pvt = L2_within_L1(raw_data, row['L1 Category'])             #generates the aggregated data for L1 present in each row 
            sheet_name = row['L1 Category']                              #stores the aggregated data for each L1 in different sheets named as the L1 Category
            pvt.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output



#MAIN FUNCTION THAT USES THE ABOVE FUNCTIONS AND CREATE A STREAMLIT APP THAT AGGREGATES ALL THE L2 W.RT L1
def main():
    # Streamlit interface
    st.title('L2 within L1 Analysis')

    # File upload for raw data
    uploaded_file = st.file_uploader("Upload a raw data file", type=["csv", "xlsx"])

    if uploaded_file is not None:
        # Read the raw data file
        if uploaded_file.name.endswith('.csv'):
            raw_data = pd.read_csv(uploaded_file)
        else:
            raw_data = pd.read_excel(uploaded_file)

        # Ask the user if they want to import a raw input excel file or want to give input manually
        use_raw_input = st.radio(
            "Do you want to import a raw input file?",
            ('No', 'Yes')
        )


        #droping the duplicates for the case when we have a concatenated data from different row-reports
        raw_data.drop_duplicates(inplace=True)

        #converting the string date to proper datetime format so that the data can be correctly sorted on the basis of dates(for extracting the latest position)
        raw_data['Date'] = pd.to_datetime(raw_data['Date'], format='%B %d, %Y')
        

        if use_raw_input == 'Yes':
            # Upload a raw input file
            raw_input_file = st.file_uploader("Upload a raw input file", type=["csv", "xlsx"])

            if raw_input_file is not None:
                # Read the raw input file
                if raw_input_file.name.endswith('.csv'):
                    raw_input_data = pd.read_csv(raw_input_file)
                else:
                    raw_input_data = pd.read_excel(raw_input_file)


                if st.button('Run Analysis'):
                    output = L2_in_L1(raw_data, raw_input_data)
                    st.success("Data has been successfully processed.")
                    st.download_button(
                        label="Download Excel file",
                        data=output,
                        file_name="output.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            # Extract unique L1 categories
            unique_L1_categories = raw_data['L1 Category'].unique().tolist()
            unique_L1_categories.append('All')  # Add 'All' option to the list

            # Select L1 category
            selected_L1 = st.selectbox("Select L1 Category", unique_L1_categories)

            if st.button('Run Analysis'):
                result = L2_within_L1(raw_data, selected_L1)

                # Save the result to a BytesIO object
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    result.to_excel(writer, index=False, sheet_name='Results')
                output.seek(0)

                st.write(result)
                st.download_button(
                    label="Download Excel file",
                    data=output,
                    file_name="result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                 )

    else:
        st.warning("Please upload a raw data file to proceed.")
