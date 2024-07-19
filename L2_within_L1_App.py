import streamlit as st
import pandas as pd
import numpy as np
import io

def L2_within_L1(raw_data, L1):
    data1 = raw_data.copy()
    data1 = data1.iloc[:, 0:21]
    
    mask1 = (data1['L1 Category'] == L1) | (L1 == "All")
    data = data1[mask1].copy()
    
    data = data.drop_duplicates()
    
    data2 = data.copy()
    data3 = data2.iloc[:, [3,4]].copy()
    data3 = data3.dropna(subset=['L2 Category'])
    data3 = data3.drop_duplicates(subset=['L2 Category']).reset_index(drop=True)
    data3['L2 Position'] = np.nan  # Initialize column to avoid SettingWithCopyWarning
    
    for i in range(data3.shape[0]):
        df1 = data2[data2['L2 Category'] == data3.loc[i, 'L2 Category']].sort_values(by='Date', ascending=False)
        data3.loc[i, 'L2 Position'] = df1.reset_index().loc[0, 'L2 Position']
        
    data = data.assign(Watch_Time=(data['Watch Time'] / 3600))
    
    piv_data = pd.pivot_table(
        data,
        values=['Views', 'Watch_Time', 'Unique Users'],
        index=['L1 Category','L2 Category'],
        aggfunc={'Views': 'sum', 'Watch_Time': 'sum', 'Unique Users':'sum'}
     )
    
    if(L1 == 'All'):
        piv_data = pd.pivot_table(
            data,
            values=['Views', 'Watch_Time', 'Unique Users'],
            index=['L2 Category'],
            aggfunc={'Views': 'sum', 'Watch_Time': 'sum', 'Unique Users':'sum'}
         )
        
    if(piv_data.shape[0] == 0):
        return piv_data
    
    piv_data = piv_data.assign(awd=np.where(piv_data['Unique Users'] == 0, np.nan, (piv_data['Watch_Time'] / piv_data['Unique Users']) * 60))
    
    piv_data_reset = piv_data.reset_index()
    df = pd.merge(piv_data_reset, data3, on='L2 Category', how='left')
    
    return df

def L2_in_L1(raw_data, raw_input):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for index, row in raw_input.iterrows():
            pvt = L2_within_L1(raw_data, row['L1 Category'])
            sheet_name = row['L1 Category']
            pvt.to_excel(writer, sheet_name=sheet_name, index=True)
    output.seek(0)
    return output

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

        # Ask the user if they want to import a raw input file
        use_raw_input = st.radio(
            "Do you want to import a raw input file?",
            ('No', 'Yes')
        )
        
        raw_data.drop_duplicates(inplace=True)

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
