import streamlit as st
import streamlit_shadcn_ui as ui
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from local_components import card_container
import up_api_helpers as up
import helpers as h
import plotly.express as px

# **************************************** SQL DB Setup **************************************** #

conn = sqlite3.connect('expenses.db')
cursor = conn.cursor()
# cursor.execute("DROP TABLE IF EXISTS transactions")
# cursor.execute("DROP TABLE IF EXISTS budget")

cursor.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, description TEXT NOT NULL, amount FLOAT NOT NULL, category TEXT, date TEXT NOT NULL)")
latest_transaction = h.get_last_transaction_date(conn)
df = up.make_dataframe(up.get_transactions(up.UP_API_URL, latest_transaction)) # Getting all transactions into a df
df.to_sql('transactions', conn, if_exists='append', index=False); # Insert df into SQL table

conn.commit()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS budget (
        name TEXT PRIMARY KEY,
        budget FLOAT NOT NULL
    )
''')

entries = [
    ('Restaurants & Takeaway', 0),
    ('Entertainment & Recreation', 0),
    ('Clothing & Accessories', 0),
    ('Health & Beauty', 0),
    ('Subscriptions & Memberships', 0),
    ('Groceries', 0),
    ('Transportation', 0),
    ('Shopping', 0),
    ('Life Admin', 0),
    ('Other', 0),
]

sql_query = "INSERT or IGNORE into budget (name, budget) VALUES (?, ?)"
cursor.executemany(sql_query, entries)

conn.commit()

# **************************************** Intro Heading **************************************** #
st.set_page_config(page_title='PennyPal', layout='wide')
st.title('PennyPal 💸')
st.markdown(':green[ ***An application to track your expenses to ensure you are keeping on top of your money*** ]')

# **************************************** Toggle Switch **************************************** #

view = ui.tabs(options=['Weekly', 'Monthly'], default_value='Weekly')

# **************************************** Metrics **************************************** #
st.write(f'## {view} Overview')
num_periods = st.slider(label='**Number of periods to show**', min_value=5, max_value=52)
if view == 'Weekly':
    display_periods = [(datetime.now() - timedelta(days=datetime.now().weekday()) - timedelta(weeks=i)).strftime('%Y-W%W') for i in range(num_periods)][::-1]
else:
    display_periods = list(reversed([(datetime(datetime.now().year, datetime.now().month, 1) - timedelta(days=i*30)).strftime('%Y-M%m') for i in range(num_periods)]))

format = "%Y-M%m" if view == "Monthly" else "%Y-W%W" 

# getting budget data from SQL table
budget_query = "SELECT * FROM budget"
budget_set = pd.read_sql(budget_query, conn)
    
# getting expenses data from SQL table
query = f"SELECT strftime('{format}', date) AS period, SUM(amount) AS expenses FROM transactions GROUP BY period ORDER BY period"
expenses_data = pd.read_sql(query, conn)  
expenses_data = expenses_data.sort_values(by='period')

# calculating all variables for the metric cards
cur_period = expenses_data.iloc[-1]['expenses']
prev_period = expenses_data.iloc[-2]['expenses'] if len(expenses_data) > 1 else 0
difference = abs(round(cur_period - prev_period, 2))
budget = budget_set['budget'].sum() if view == 'Weekly' else budget_set['budget'].sum() * 4
sign = '-' if cur_period < prev_period else '+'
budget_difference = abs(round(budget - cur_period, 2))
over_under = "over" if budget < cur_period else "under"
time_period = 'week' if view == 'Weekly' else 'month'

# processing the data to be show on bar graph
expenses_data.set_index('period', inplace=True)
to_display = {'Period': [], 'Spending': []}
for period in display_periods:
    spending = expenses_data.loc[period]['expenses'] if period in expenses_data.index else 0
    to_display['Period'].append(period)
    to_display['Spending'].append(spending)
display = pd.DataFrame(to_display)

cols = st.columns(3)
with cols[0]:
    ui.metric_card(title=f'Total {view} Spend', content=f'${round(cur_period, 2)}', description=f'{sign}${difference} from last {time_period}')
with cols[1]:
    ui.metric_card(title=f'Total {view} Budget', content=f'${budget}', description=f'${budget_difference} {over_under} budget')
with cols[2]:
    ui.metric_card(title=f'Average {view} Spend', content=f'${round(display["Spending"].mean(), 2)}', description=f'Over the past {len(display)} {time_period}s ')

# **************************************** Chart **************************************** #
# Define the Vega-Lite specification
vega_lite_spec = {
    "mark": { "type": "bar", "cornerRadiusEnd": 6 },
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
            "field": "Period", 
            "type": "ordinal",
            "axis": {
                "labelAngle": 0,
                "title": f'{period}s',
                "grid": False
            },
            "sort": display_periods
        },
        "y": {
            "field": "Spending", 
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

with card_container():
    st.vega_lite_chart(display, vega_lite_spec, use_container_width=True)

# **************************************** All Transactions **************************************** #

# getting expenses data from SQL table
query = f""" 
    SELECT *
    FROM transactions
    ORDER BY date DESC
"""
df = pd.read_sql(query, conn)

if view == 'Weekly':
    periods = set([datetime.fromisoformat(date).strftime('%Y-W%W') for date in df['date']])
    periods = list(reversed(sorted(periods)))
else:
    periods = set([datetime.fromisoformat(date).strftime('%m/%y') for date in df['date']])
    periods = [datetime.strptime(period, '%m/%y') for period in periods]
    periods = reversed(sorted(periods))
    periods = [date.strftime('%B %Y') for date in periods]

period = st.selectbox(label="**Select Time Period**", options=periods, index=0)

df['date_time'] = pd.to_datetime(df['date'], utc=True)
df['date'] = df['date_time'].dt.strftime('%d %B %Y')
df['week'] = df['date_time'].dt.strftime('%Y-W%W')
df['month'] = df['date_time'].dt.strftime('%B %Y')
df = df[df['week'] == period] if view == 'Weekly' else df[df['month'] == period]
df.drop(columns=['date_time', 'week', 'month'], inplace=True)
table_height = 750 if view == 'Weekly' else 1000
edited_df = st.data_editor(
                df,
                column_config={
                    "amount": st.column_config.NumberColumn(
                        "Amount",
                        format="$%.2f"
                    ),
                    "category": st.column_config.SelectboxColumn(
                        "Category",
                        options=[
                                'Food',
                                'Entertainment and Recreation',
                                'Clothing and Accessories',
                                'Health and Beauty',
                                'Subscriptions and Memberships',
                                'Groceries',
                                'Transportation',
                                'Shopping',
                                'Life Admin',
                                'Other',
                        ]
                    )
                },
                use_container_width=True,
                hide_index=True, 
                height=table_height
            )

if st.button("Save Changes", type="primary"):
    try:
        for id, row in edited_df.iterrows():
            h.update_entry(row, cursor)
        conn.commit()
        st.success("Entries updated successfully", icon='✅')
    except Exception as e:
        st.error("Error occured whilst attempting to update transactions")

# **************************************** Delete Expenses **************************************** #

delete_id = st.number_input('Delete Transaction', value=0)
if st.button("Delete Expense", type="primary"):
    delete_query = 'DELETE FROM transactions WHERE id = ?'
    cursor.execute(delete_query, (delete_id,))
    if cursor.rowcount == 0:
        st.error(f'Transaction with ID {int(delete_id)} does not exist in the database', icon='⚠️')
    else:
        st.success(f'Transaction with ID {int(delete_id)} deleted from databse', icon='✅')
    conn.commit()



# **************************************** Budget Chart **************************************** #
df['category'] = df['category'].fillna('Uncategorised')
categories = df.groupby('category')['amount'].sum()
categories = categories.reset_index()
categories.columns = ['category', 'amount'];
print(categories)
total_spend = categories['amount'].sum()
max_index = categories['amount'].idxmax()
largest_category = categories.loc[max_index, 'category']
largest_amount = categories.loc[max_index, 'amount']


st.write(f'## Spending Breakdown for {period}')

with card_container():
    fig = px.pie(categories, values='amount', names='category')

    fig.update_traces(
        hole=0.5,
        domain=dict(x=[0, 0.5], y=[0, 1])
    )
    fig.update_layout(
        legend_font_size=20,  # Legend font size
        font=dict(size=18),  # General font size (for labels)
        legend=dict(
            orientation="v",  # Horizontal legend
            yanchor="middle",  # Anchor the legend at the bottom
            y=0.5,  # Push the legend below the chart
            xanchor="left",  # Center horizontally
            x=0.6  # Center the legend
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    cols = st.columns(2)
    with cols[0]:
        ui.metric_card(title=f'Total Spending', content=f'${round(total_spend, 2)}', description=f'Spent during the period of {period}')
    with cols[1]:
        ui.metric_card(title=f'Higest Expense', content=f'${round(largest_amount, 2)}', description=f'Spent on {largest_category}')
