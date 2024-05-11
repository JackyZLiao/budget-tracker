import streamlit as st
import streamlit_shadcn_ui as ui
import sqlite3
import pandas as pd
import datetime

# Connecting to SQL database 
conn = sqlite3.connect('expenses.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        amount FLOAT NOT NULL,
        category TEXT NOT NULL,
        date DATE NOT NULL,
        note TEXT
    )
''')

# **************************************** Intro Heading **************************************** #
st.set_page_config(page_title='PennyPal', layout='wide')
st.title('PennyPal 💸')
st.markdown(':green[ ***An application to track your expenses to ensure you are keeping on top of your money*** ]')
st.divider()

# **************************************** Toggle Switch **************************************** #

view = ui.tabs(options=['Weekly', 'Monthly'], default_value='Weekly')

# **************************************** Metrics **************************************** #
st.write(f'## {view} Overview')

format = "%m/%Y" if view == "Monthly" else "W%W %Y"
# getting expenses data from SQL table
query = f""" 
    SELECT 
        strftime('{format}', date) AS period,
        SUM(amount) AS expenses
    FROM expenses
    GROUP BY period
    ORDER BY period
"""
expenses_data = pd.read_sql(query, conn)            

# calculating all variables for the metric cards
cur_period = expenses_data.iloc[-1]['expenses']
prev_period = expenses_data.iloc[-2]['expenses'] if len(expenses_data) > 1 else 0
difference = abs(round(cur_period - prev_period, 2))
budget = 250 # need to change
sign = '-' if cur_period < prev_period else '+'
budget_difference = abs(round(budget - cur_period, 2))
over_under = "over" if budget < cur_period else "under"
average = round(expenses_data['expenses'].mean(), 2)
period = 'week' if view == 'Weekly' else 'month'

cols = st.columns(3)
with cols[0]:
    ui.metric_card(title=f'Total {view} Spend', content=f'${cur_period}', description=f'{sign}${difference} from last {view}')
with cols[1]:
    ui.metric_card(title=f'Total {view} Budget', content=f'${budget}', description=f'${budget_difference} {over_under} budget')
with cols[2]:
    ui.metric_card(title=f'Average {view} Spend', content=f'${average}', description=f'Over the past {len(expenses_data)} {period}s ')

# **************************************** Chart **************************************** #
st.write(f'## {view} Spending Insight')

# Define the Vega-Lite specification
vega_lite_spec = {
    "mark": { "type": "bar", "cornerRadiusEnd": 10 },
    "config": {
        "axis": {
            "titleFontSize": 18,
            "labelFontSize": 14,
            "titleFontWeight": "bold",
            "labelFontWeight": "bold"
        }
    },
    "encoding": {
        "x": {
            "field": "period", 
            "type": "ordinal",
            "axis": {
                "labelAngle": 0,
                "title": f'{period}s',
                "grid": False
            }
        },
        "y": {
            "field": "expenses", 
            "type": "quantitative",
            "axis": {
                "title": "Spending",
                # "grid": False
            }
        },
        "color": {"value": "black"},
        "text": {"field": "expenses", "type": "quantitative", "color": {"value": "white"}},
    },
    "height": 750,
}

with st.container(border=True):
    st.vega_lite_chart(expenses_data, vega_lite_spec, use_container_width=True)

# **************************************** Add Expenses **************************************** #

st.write(f'## Add Expense')

cols = st.columns(4)
with cols[0]:
    name = st.text_input("Expense *")
with cols[1]:
    amount = st.number_input("Amount *")
with cols[2]:
    category = st.selectbox(
        "Expense Category *",
        ('Restaurants & Takeaway',
        'Entertainment & Recreation',
        'Clothing & Accessories',
        'Fitness & Health',
        'Beauty & Hair',
        'Groceries',
        'Transportation',
        'Shopping',
        'Life Admin',
        'Other')
    )
with cols[3]:
    date = st.date_input("Date *")

note = st.text_input("Notes")

if st.button("Add Expense", type="primary"):
    if name and amount and category and date:
        cursor.execute("INSERT INTO expenses (name, amount, category, date, note) VALUES (?, ?, ?, ?, ?)", (name, amount, category, date, note))
        conn.commit()
        st.success('Expense successfully added', icon='✅')
    else:
        st.warning("Please fill out all required fields before submitting", icon='⚠️')
st.divider()

# **************************************** All Transactions **************************************** #
st.write('## All Transactions')

# getting expenses data from SQL table
query = f""" 
    SELECT *
    FROM expenses
    ORDER BY date DESC
"""
df = pd.read_sql(query, conn)

if view == 'Weekly':
    periods = list(set([datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%W') for date in list(df['date'])]))
    periods = map(lambda x: f'Week {x}', periods)
    periods = list(sorted(periods))
else:
    periods = list(set([datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%m/%y') for date in list(df['date'])]))
    periods = map(lambda x: datetime.datetime.strptime(x, '%m/%y').strftime('%B \'%y'), periods)


cols = st.columns(2)
with cols[0]:
    period = st.selectbox(label="Select Time Period", options=periods, index=0)
with cols[1]:
    sort_by = st.selectbox(label="Sort By", options=df.columns[1:-1], index=3)


df['date_time'] = pd.to_datetime(df['date'])
df['week'] = df['date_time'].dt.strftime('%W')
df['week'] = df['week'].astype(int)
df['month'] = df['date_time'].dt.strftime('%B \'%y')
df = df[df['week'] == int(period[-2:])] if view == 'Weekly' else df[df['month'] == period]
df.drop(columns=['date_time', 'week', 'month'], inplace=True)
df = df.sort_values(by=f'{sort_by}')
print(df)
with st.container(border=True):
    ui.table(data=df)
# st.divider()

# **************************************** Budget **************************************** #

df = df.groupby('category')['amount'].sum()
print(df)
st.write(f'## Budget')
cols = st.columns(2)
with cols[0]:
    st.write('##### Restaurants and Takeaway: \$50 out of $100')
    st.progress(0.5)

    st.write('')
    st.write('##### Clothing & Accessories: $50 out of ')
    st.progress(0.75)

    st.write('')
    st.write('##### Fitness & Health: $50')
    st.progress(0.6)

    st.write('')
    st.write('##### Beauty & Hair: $50')
    st.progress(0.1)

    st.write('')
    st.write('##### Groceries: $50')
    st.progress(1.0)
with cols[1]:
    st.write('##### Transportation: $50')
    st.progress(0.5)

    st.write('')
    st.write('##### Shopping: $50')
    st.progress(1.0)

    st.write('')
    st.write('##### Life Admin: $50')
    st.progress(1.0)

    st.write('')
    st.write('##### Entertain & Recreation: $50')
    st.progress(0.7)

    st.write('')
    st.write('##### Other: $50')
    st.progress(1.0)

st.write('')
st.button('Edit Budget Amounts')
progress = 0.75  # Example progress value

# Calculate the color based on progress value
red_value = int(255 * (1 - progress))
green_value = int(255 * progress)
    
st.markdown(
    """
    <style>
        .stProgress > div > div > div > div {
            background-image: linear-gradient(to right, black , black);
        }
    </style>""",
    unsafe_allow_html=True,
)
# TODO: Bar chart of weekly/monthly expense
# TODO: Budget breakdown - categories
# TODO: Table of expenses
# TODO: delete expense
