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

cols = st.columns(2)
with cols[0]:
    period = st.selectbox(label="**Select Time Period**", options=periods, index=0)
with cols[1]:
    sort_by = st.selectbox(label="**Sort By**", options=df.columns[1:], index=3)

df = df.sort_values(by=f'{sort_by}')
df['date_time'] = pd.to_datetime(df['date'], utc=True)
df['date'] = df['date_time'].dt.strftime('%d %B %Y')
df['week'] = df['date_time'].dt.strftime('%Y-W%W')
df['month'] = df['date_time'].dt.strftime('%B %Y')
df = df[df['week'] == period] if view == 'Weekly' else df[df['month'] == period]
df.drop(columns=['date_time', 'week', 'month'], inplace=True)
print(df)
with card_container():
    ui.table(data=df)

# **************************************** Modify Expenses **************************************** #
outer_cols = st.columns(2)

with outer_cols[0]:
    st.write(f'## Modify Expense')
    modify_id = st.number_input('Modfiy ID', value=None)
    if ui.button("Modify Expense", variant="destructive"):
        delete_query = 'DELETE FROM expenses WHERE id = ?'
        cursor.execute(delete_query, (id,))
        if cursor.rowcount == 0:
            st.error(f'Transaction with ID {int(id)} does not exist in the database', icon='⚠️')
        else:
            st.success(f'Transaction with ID {int(id)} deleted from databse', icon='✅')
        conn.commit()

    # st.write(f'## Modify Expense')
    # cols = st.columns(2)
    # with cols[0]:
    #     name = st.text_input("Expense *", placeholder='Name of expense')
    #     category = st.selectbox(
    #         "Expense Category *",
    #         ('Restaurants & Takeaway',
    #         'Entertainment & Recreation',
    #         'Clothing & Accessories',
    #         'Health & Beauty',
    #         'Subscriptions & Memberships',
    #         'Groceries',
    #         'Transportation',
    #         'Shopping',
    #         'Life Admin',
    #         'Other')
    #         , index=None
    #         , placeholder='Select a category'
    #     )
    # with cols[1]:
    #     amount = st.number_input("Amount *")
    #     date = st.date_input("Date *")
    # note = st.text_input("Notes", placeholder='Write any notes related to expense')

    # st.write('')
    # if ui.button("Add Expense", key="clk_btn"):
    #     if name and amount and category and date:
    #         cursor.execute("INSERT INTO expenses (name, amount, category, date, note) VALUES (?, ?, ?, ?, ?)", (name, amount, category, date, note))
    #         conn.commit()
    #         st.success('Expense successfully added', icon='✅')
    #     else:
    #         st.warning("Please fill out all required fields before submitting", icon='⚠️')
with outer_cols[1]:
    st.write(f'## Delete Expense')
    delete_id = st.number_input('Delete ID', value=None)
    if ui.button("Delete Expense", variant="destructive"):
        delete_query = 'DELETE FROM expenses WHERE id = ?'
        cursor.execute(delete_query, (id,))
        if cursor.rowcount == 0:
            st.error(f'Transaction with ID {int(id)} does not exist in the database', icon='⚠️')
        else:
            st.success(f'Transaction with ID {int(id)} deleted from databse', icon='✅')
        conn.commit()



# **************************************** Budget Chart **************************************** #

categories = df.groupby('category')['amount'].sum()
categories = categories.reset_index()
categories.columns = ['category', 'amount'];

st.write(f'## Spending by Category')

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


#budget_multiplier = 1 if view == 'Weekly' else 4
# r_t_target = budget_set[budget_set['name'] == 'Restaurants & Takeaway']['budget'].iloc[0] * budget_multiplier
# c_a_target = budget_set[budget_set['name'] == 'Clothing & Accessories']['budget'].iloc[0] * budget_multiplier
# h_b_target = budget_set[budget_set['name'] == 'Health & Beauty']['budget'].iloc[0] * budget_multiplier
# s_m_target = budget_set[budget_set['name'] == 'Subscriptions & Memberships']['budget'].iloc[0] * budget_multiplier
# e_r_target = budget_set[budget_set['name'] == 'Entertainment & Recreation']['budget'].iloc[0] * budget_multiplier
# la_target = budget_set[budget_set['name'] == 'Life Admin']['budget'].iloc[0] * budget_multiplier
# g_target = budget_set[budget_set['name'] == 'Groceries']['budget'].iloc[0] * budget_multiplier
# t_target = budget_set[budget_set['name'] == 'Transportation']['budget'].iloc[0] * budget_multiplier
# s_target = budget_set[budget_set['name'] == 'Shopping']['budget'].iloc[0] * budget_multiplier
# o_target = budget_set[budget_set['name'] == 'Other']['budget'].iloc[0] * budget_multiplier

# r_t_spent = round(budget_spent['Restaurants & Takeaway'], 2) if 'Restaurants & Takeaway' in budget_spent.index else 0
# c_a_spent = round(budget_spent['Clothing & Accessories'], 2) if 'Clothing & Accessories' in budget_spent.index else 0
# h_b_spent = round(budget_spent['Health & Beauty'], 2) if 'Health & Beauty' in budget_spent.index else 0
# s_m_spent = round(budget_spent['Subscriptions & Memberships'], 2) if 'Subscriptions & Memberships' in budget_spent.index else 0
# e_r_spent = round(budget_spent['Entertainment & Recreation'], 2) if 'Entertainment & Recreation' in budget_spent.index else 0
# la_spent = round(budget_spent['Life Admin'], 2) if 'Life Admin' in budget_spent.index else 0
# g_spent = round(budget_spent['Groceries'], 2) if 'Groceries' in budget_spent.index else 0
# t_spent = round(budget_spent['Transportation'], 2) if 'Transportation' in budget_spent.index else 0
# s_spent = round(budget_spent['Shopping'], 2) if 'Shopping' in budget_spent.index else 0
# o_spent = round(budget_spent['Other'], 2) if 'Other' in budget_spent.index else 0

# colour = 'green'
# with card_container():
#     cols = st.columns(2)
#     with cols[0]:
#         colour = 'red' if r_t_spent > r_t_target else 'green'
#         st.write(f'##### Restaurants and Takeaway: :{colour}[\${r_t_spent}] out of ${r_t_target}')
#         st.progress(r_t_spent / r_t_target if r_t_spent < r_t_target else 0 if r_t_target == 0 else 1.0)

#         st.write('')
#         colour = 'red' if c_a_spent > c_a_target else 'green'
#         st.write(f'##### Clothing & Accessories: :{colour}[\${c_a_spent}] out of ${c_a_target}')
#         st.progress(c_a_spent / c_a_target if c_a_spent < c_a_target else 0 if c_a_target == 0 else 1.0)

#         st.write('')
#         colour = 'red' if h_b_spent > h_b_target else 'green'
#         st.write(f'##### Health & Beauty: :{colour}[\${h_b_spent}] out of ${h_b_target}')
#         st.progress(h_b_spent / h_b_target if h_b_spent < h_b_target else 0 if h_b_target == 0 else 1.0)

#         st.write('')
#         colour = 'red' if s_m_spent > s_m_target else 'green'
#         st.write(f'##### Subscriptions & Memberships: :{colour}[\${s_m_spent}] out of ${s_m_target}')
#         st.progress(s_m_spent / s_m_target if s_m_spent < s_m_target else 0 if s_m_target == 0 else 1.0)

#         st.write('')
#         colour = 'red' if g_spent > g_target else 'green'
#         st.write(f'##### Groceries: :{colour}[\${g_spent}] out of ${g_target}')
#         st.progress(g_spent / g_target if g_spent < g_target else 0 if g_spent == 0 else 1.0)
#     with cols[1]:
#         colour = 'red' if t_spent > t_target else 'green'
#         st.write(f'##### Transportation: :{colour}[\${t_spent}] out of ${t_target}')
#         st.progress(t_spent / t_target if t_spent < t_target and t_spent > 0 else 0 if t_spent == 0 else 1.0)

#         st.write('')
#         colour = 'red' if s_spent > s_target else 'green'
#         st.write(f'##### Shopping: :{colour}[\${s_spent}] out of ${s_target}')
#         st.progress(s_spent / s_target if s_spent < s_target else 0 if s_spent == 0 else 1.0)

#         st.write('')
#         colour = 'red' if la_spent > la_target else 'green'
#         st.write(f'##### Life Admin: :{colour}[\${la_spent}] out of ${la_target}')
#         st.progress(la_spent / la_target if la_spent < la_target else 0 if la_spent == 0 else 1.0)

#         st.write('')
#         colour = 'red' if e_r_spent > e_r_target else 'green'
#         st.write(f'##### Entertain & Recreation: :{colour}[\${e_r_spent}] out of ${e_r_target}')
#         st.progress(e_r_spent / e_r_target if e_r_spent < e_r_target else 0 if e_r_spent == 0 else 1.0)

#         st.write('')
#         colour = 'red' if o_spent > o_target else 'green'
#         st.write(f'##### Other: :{colour}[\${o_spent}] out of ${o_target}')
#         st.progress(o_spent / o_target if o_spent < o_target else 0 if o_target == 0 else 1.0)
    
#     colour = 'red' if round(budget_spent.sum(), 2) > budget else 'green'
#     st.write('')
#     st.write(f'## Total Spending: :{colour}[\${round(budget_spent.sum(), 2)}] out of \${budget}')

# budget_targets = {}
# with st.expander("**Edit Weekly Budget Targets**"):
#     cols = st.columns(5)
#     with cols[0]:
#         budget_targets['Restaurants & Takeaway'] = st.number_input('**Restaurants & Takeaway**', value=r_t_target)
#         budget_targets['Transportation'] = st.number_input('**Transportation**', value=t_target)
#     with cols[1]:
#         budget_targets['Life Admin'] = st.number_input('**Life Admin**', value=la_target)
#         budget_targets['Subscriptions & Memberships'] = st.number_input('**Subscriptions & Memberships**', value=s_m_target)
#     with cols[2]:
#         budget_targets['Clothing & Accessories'] = st.number_input('**Clothing & Accessories**', value=c_a_target)
#         budget_targets['Shopping'] = st.number_input('**Shopping**', value=s_target)
#     with cols[3]:
#         budget_targets['Health & Beauty'] = st.number_input('**Health & Beauty**', value=h_b_target)
#         budget_targets['Entertainment & Recreation'] = st.number_input('**Entertainment & Recreation**', value=e_r_target)
#     with cols[4]:
#         budget_targets['Groceries'] = st.number_input('**Groceries**', value=g_target)
#         budget_targets['Other'] = st.number_input('**Other**', value=o_target)
#     st.write('')

#     if ui.button('Set Budget', variant='outline', key='outline'):
#         for key, value in budget_targets.items():
#             update_statement = '''
#                 UPDATE budget
#                 SET budget = ?
#                 WHERE name = ?
#             '''
#             cursor.execute(update_statement, (value, key))
#         conn.commit()
# st.markdown(
#     """
#     <style>
#         .stProgress > div > div > div > div {
#             background-image: linear-gradient(to right, black , black);
#         }
#     </style>""",
#     unsafe_allow_html=True,
# )