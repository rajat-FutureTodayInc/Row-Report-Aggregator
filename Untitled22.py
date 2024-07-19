import streamlit as st
import L2_within_L1_App
import PlayList_within_L2_App
import ActionPlayList_within_PlayList_App
import Node_in_PlayList_App
import Node_within_ActionPlayList_App

def main():
    st.sidebar.title("Aggregation Tools")
    
    # Initialize session state for page if not already set
    if 'page' not in st.session_state:
        st.session_state.page = "Home"

    # Sidebar for navigation
    page = st.sidebar.radio(
        "Go to",
        ["Home", "L2 within L1", "PlayList within L2", "ActionPlayList within PlayList", "Node within PlayList", "Node within ActionPlayList"],
        index=["Home", "L2 within L1", "PlayList within L2", "ActionPlayList within PlayList", "Node within PlayList", "Node within ActionPlayList"].index(st.session_state.page)
    )
    
    # Update session state when a new page is selected from the sidebar
    if page != st.session_state.page:
        st.session_state.page = page

    # Display content based on selected page
    if st.session_state.page == "Home":
        st.title("Welcome to the Aggregation Tools")
        st.write("Choose an aggregation tool from the sidebar.")
        
        # Buttons for page navigation
        if st.button("L2 within L1"):
            st.session_state.page = "L2 within L1"
            st.experimental_rerun()
        if st.button("PlayList within L2"):
            st.session_state.page = "PlayList within L2"
            st.experimental_rerun()
        if st.button("ActionPlayList within PlayList"):
            st.session_state.page = "ActionPlayList within PlayList"
            st.experimental_rerun()
        if st.button("Node within PlayList"):
            st.session_state.page = "Node within PlayList"
            st.experimental_rerun()
        if st.button("Node within ActionPlayList"):
            st.session_state.page = "Node within ActionPlayList"
            st.experimental_rerun()
            
    elif st.session_state.page == "L2 within L1":
        L2_within_L1_App.main()

    elif st.session_state.page == "PlayList within L2":
        PlayList_within_L2_App.main()

    elif st.session_state.page == "ActionPlayList within PlayList":
        ActionPlayList_within_PlayList_App.main()

    elif st.session_state.page == "Node within PlayList":
        Node_in_PlayList_App.main()

    elif st.session_state.page == "Node within ActionPlayList":
        Node_within_ActionPlayList_App.main()

if __name__ == "__main__":
    main()
