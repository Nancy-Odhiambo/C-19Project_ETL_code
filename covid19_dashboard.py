import streamlit as st
from sqlalchemy import create_engine
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Streamlit Page Styling
st.set_page_config(page_title="Mexican COVID-19 Analysis Dashboard", layout="wide")
st.markdown("""
    <style>
    .main { 
        background-color: #2f2f2f;
        max-width: 100%;
    }
    h1, h2, h3, h4, h5, h6 { 
        color: #A9A9A9 !important;
        font-weight: bold !important;
        text-align: center;
    }
    .stPlotlyChart > div { 
        background-color: #2f2f2f !important;
        border-radius: 10px;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        text-align: center;
    }
    .css-1v0mbdj {
        max-width: 100%;
    }
    .stSelectbox > div {
        padding: 0.2rem;
        margin-bottom: 0.5rem;
        width: 50%;
        margin-left: auto;
        margin-right: auto;
    }
    .js-plotly-plot .plotly, .js-plotly-plot .plotly div {
        background-color: #4f4f4f !important;
    }
    .block-container {
        max-width: 95%;
        padding: 1rem 3rem;
    }
    .stMarkdown p {
        color: #A9A9A9;
        text-align: justify;
        max-width: 100%;
    }
    .stDataFrame {
        background-color: #4f4f4f !important;
    }
    .stDataFrame div[data-testid="stDataFrameContainer"] {
        background-color: #4f4f4f !important;
    }
    </style>
""", unsafe_allow_html=True)

# Customizing the Dashboard Title
st.markdown("<h1 style='color: #A9A9A9; font-weight: bold; text-align: center;'>Mexican COVID-19 Patient Analysis Dashboard</h1>", unsafe_allow_html=True)

# Data loading from postgres
@st.cache_resource
def get_engine():
    DATABASE_URL = "postgresql+psycopg2://kestra:k3str4@127.0.0.1:5432/kestra"
    return create_engine(DATABASE_URL)

@st.cache_data(show_spinner="Loading data...", ttl=3600)
def load_data():
    query = "SELECT * FROM transformed_data"
    return pd.read_sql_query(query, get_engine())

# Loading the data set into the local environment
covid_data = load_data()

# Summary statistics for age variable
@st.cache_data
def get_age_summary(data):
    return data['age'].describe()

age_summary = get_age_summary(covid_data)

plot_template = {
    'layout': {
        'plot_bgcolor': '#4f4f4f',
        'paper_bgcolor': '#4f4f4f',
        'font': {'color': 'white'},
        'margin': {'t': 60},
        'yaxis': {'title': 'Proportion of Patient Outcome'}
    }
}

# Visualizing severity of patient covid results by status outcome(Dead, Alive)
@st.cache_data
def create_severity_outcomes_plot(data):
    severity_outcomes = data.groupby('clasiffication_final')['status'].value_counts(normalize=True).unstack().loc[['Mild', 'Moderate', 'Severe']]
    severity_outcomes_long = severity_outcomes.reset_index().melt(id_vars='clasiffication_final', value_vars=['Alive', 'Dead'], var_name='Outcome', value_name='Proportion')
    fig = px.bar(severity_outcomes_long, x='clasiffication_final', y='Proportion', color='Outcome', 
                color_discrete_map={'Alive': 'lightblue', 'Dead': 'orange'}, 
                barmode='group', title='<b style="color:#A9A9A9">Patient Outcomes by COVID-19 Severity</b>',
                template=plot_template)
    fig.update_yaxes(title_text='Proportion of Patient Outcome')
    return fig

fig1 = create_severity_outcomes_plot(covid_data)

# Analysing different patient outcomes by age group
@st.cache_data
def create_age_group_plot(data):
    bins = [0, 18, 35, 50, 65, 80, 120]
    labels = ['0-18', '19-35', '36-50', '51-65', '66-80', '81+']
    data['age_group'] = pd.cut(data['age'], bins=bins, labels=labels, right=False)
    indicators = {'icu': 'Yes', 'intubed': 'Yes', 'status': 'Dead'}
    proportions_list = []
    for column, target_value in indicators.items():
        proportions = (data[data[column] == target_value].groupby('age_group', observed=True).size() / 
                    data.groupby('age_group', observed=True).size())
        prop_df = proportions.reset_index()
        prop_df['Indicator'] = column
        proportions_list.append(prop_df)
    proportions_df = pd.concat(proportions_list)
    proportions_df['Indicator'] = proportions_df['Indicator'].map({'icu': 'ICU Admission', 'intubed': 'Intubated', 'status': 'Death'})
    fig = px.bar(proportions_df, x='age_group', y=0, color='Indicator', 
                color_discrete_map={'ICU Admission': 'lightblue', 'Intubated': 'navy', 'Death': 'orange'},
                barmode='group', title='<b style="color:#A9A9A9">Proportion of ICU Admission, Intubation, and Death by Age Group</b>',
                template=plot_template)
    fig.update_yaxes(title_text='Proportion of Patient Outcome')
    return fig

fig2 = create_age_group_plot(covid_data)

# Checking the density distribution for patient outcomes by age
st.header("Patient Analysis")
col3, col4 = st.columns(2)

with col4:
    status_columns = ['icu', 'intubed', 'admission_status', 'status']
    st.markdown("<h4 style='text-align: center; margin-bottom: 0.5rem; color: #A9A9A9;'>Select a Category for Age Distribution Analysis</h4>", unsafe_allow_html=True)
    selected_violin = st.selectbox("", status_columns, index=0, label_visibility="collapsed")
    
    @st.cache_data
    def create_violin_plot(data, selected_column):
        fig = px.violin(data, y='age', x=selected_column, color=selected_column, 
                      color_discrete_map={'Yes': 'navy', 'No': 'lightblue', 'Alive': 'lightblue', 'Dead': 'orange'},
                      box=True, points='all', title=f'<b style="color:#A9A9A9">Age Distribution by {selected_column.capitalize()}</b>',
                      template=plot_template)
        fig.update_yaxes(title_text='Age')
        return fig

    fig3 = create_violin_plot(covid_data, selected_violin)
    st.plotly_chart(fig3, use_container_width=True)

with col3:
    st.plotly_chart(fig2, use_container_width=True)

# Correlation matrix os status variables with other data set features
@st.cache_data
def create_correlation_plot(data):
    data_copy = data.copy()
    def encode_column(col):
        if col in data_copy.columns:
            unique_vals = data_copy[col].unique()
            if set(unique_vals).issubset({'Yes', 'No'}):
                data_copy[col] = data_copy[col].map({'Yes': 1, 'No': 0})
            elif col == 'status':
                data_copy[col] = data_copy[col].map({'Alive': 1, 'Dead': 0})
            elif col == 'sex':
                data_copy[col] = data_copy[col].map({'Female': 0, 'Male': 1})
            elif col == 'admission_status':
                data_copy[col] = data_copy[col].map({'No': 0, 'Yes': 1})
    for col in data_copy.columns:
        encode_column(col)
    data_copy = pd.get_dummies(data_copy, columns=['clasiffication_final'], drop_first=True)
    numeric_data = data_copy.select_dtypes(include=['number'])
    correlation_with_status = numeric_data.corr()['status'].drop('status').sort_values(ascending=False)
    fig = px.bar(x=correlation_with_status.values, y=correlation_with_status.index, orientation='h', 
                color=correlation_with_status.values,
                color_continuous_scale=['orange', 'lightblue', 'navy'],
                title='<b style="color:#A9A9A9">Correlation of Comorbidities with Patient Outcome (Alive=1, Dead=0)</b>',
                template=plot_template)
    fig.update_xaxes(title_text='Correlation Coefficient')
    fig.update_yaxes(title_text='Comorbidities')
    return fig

fig4 = create_correlation_plot(covid_data)

# Pie chart plotting the perecntage admission_status i.e. admitted and Not admitted patients
@st.cache_data
def create_pie_chart(data):
    admission_counts = data['admission_status'].value_counts()
    labels = admission_counts.index.tolist()
    return px.pie(names=labels, values=admission_counts, 
                color_discrete_sequence=['lightblue', 'orange'],
                title='<b style="color:#A9A9A9">Admission Status Distribution</b>', 
                hole=0.3, template=plot_template)

fig6 = create_pie_chart(covid_data)

# Age summary statistics
st.header("Summary Statistics and Outcomes")
col1, col2 = st.columns(2)
with col1:
    st.subheader("Summary Statistics for Age")
    age_summary_df = age_summary.to_frame(name="Age Statistics")
    st.dataframe(age_summary_df.style.set_properties(**{
        'background-color': '#4f4f4f',
        'color': 'white',
        'border-color': '#2f2f2f',
        'height': '35px'
    }))
with col2:
    st.plotly_chart(fig1, use_container_width=True)

col5, col6 = st.columns(2)
with col5:
    st.plotly_chart(fig4, use_container_width=True)
with col6:
    st.plotly_chart(fig6, use_container_width=True)