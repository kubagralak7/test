import yfinance
from dash import Dash, dcc, html, Input, Output, callback, dash_table
import plotly.express as px
import pandas as pd
import yfinance as yf

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

def pobierz_do_spacji(napis):
    indeks_spacji = napis.find(' ')
    return napis[:indeks_spacji]

def replace_percent(value):
    return value.replace('%', '')

def create_ETF_information_dict(ticker):
    link = 'https://etfdb.com/etf/{}/'
    link = link.format(ticker)
    dfs = pd.read_html(link)
    ETF_parametrs = {}
    ETF_parametrs['Segment'] = dfs[0].iloc[0, 1]
    ETF_parametrs['Category'] = dfs[0].iloc[1, 1]
    ETF_parametrs['Focus'] = dfs[0].iloc[2, 1]
    ETF_parametrs['Niche'] = dfs[0].iloc[3, 1]
    ETF_parametrs['Companies_capitalization_structure'] = dfs[6].iloc[:,[0,1]]
    ETF_parametrs['Holdings structure'] = dfs[5].iloc[:,[0,1]]
    ETF_parametrs['Top 10 holdings'] = dfs[4][['Symbol Symbol', '% Assets % Assets']].rename(columns={'Symbol Symbol': 'Symbol', '% Assets % Assets': '% Assets'}).head(10)
    ETF_parametrs['Returns'] = dfs[10].iloc[:, [0, 1]]
    ETF_parametrs['Countries'] = dfs[12]
    ETF_parametrs['Countries']['Percentage'] = ETF_parametrs['Countries']['Percentage'].apply(replace_percent)
    ETF_parametrs['Sectors'] = dfs[13]
    ETF_parametrs['Sectors']['Percentage'] = ETF_parametrs['Sectors']['Percentage'].apply(replace_percent)
    #######
    yf_ticker = yf.Ticker(ticker)
    df_value = yf_ticker.history(period='max')[['Close']]
    df_value = df_value.reset_index()
    df_value['Date'] = df_value['Date'].dt.date
    first_month_value = df_value.head(30)
    first_month_value = first_month_value['Close'].sum() / 30
    last_month_value = df_value.tail(30)
    last_month_value = last_month_value['Close'].sum() / 30
    value_increase = str(round(((last_month_value - first_month_value) / first_month_value) * 100, 2)) + ' %'
    years = round((df_value['Date'].max() - df_value['Date'].min()).total_seconds() / (365.25 * 24 * 3600), 1)
    ETF_parametrs['Years'] = years
    ETF_parametrs['Value increase'] = value_increase
    return ETF_parametrs

largest_ETFs = pd.read_html('https://etfdb.com/compare/market-cap/')[0]
largest_ETFs = largest_ETFs.drop(labels='Avg Daily Share Volume (3mo)', axis=1)
largest_ETFs_Tickers = largest_ETFs['Symbol'].head(30).values.tolist()
ETF_names = largest_ETFs['Name']
largest_ETFs_Tickers_names = [largest_ETFs_Tickers[i] + ' - ' + ETF_names[i] for i in range(len(largest_ETFs_Tickers))]
print(largest_ETFs_Tickers_names)
ETFs_to_remove = ['BND - Vanguard Total Bond Market ETF', 'GLD - SPDR Gold Shares', 'AGG - iShares Core U.S. Aggregate Bond ETF']
for ETF in ETFs_to_remove:
    largest_ETFs_Tickers_names.remove(ETF)

app = Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

app.layout = html.Div(id='container', children=[
    html.Div(id='ETF_selection_container', children=[
        dcc.Dropdown(largest_ETFs_Tickers_names, 'SPY - SPDR S&P 500 ETF Trust', multi=True, id='my_input',
                     style={'height': '55px'}),
    ]),
    html.Div(id='line_graphs_container', children=[
        html.Div(id='line_graphs', children=[
            dcc.Graph(id='main_graph')
        ])
    ]),
    html.Div(id='ETF_information_container')
])
@callback(
    Output('main_graph', 'figure'),
    Input('my_input', 'value')
)
def update_figure(choosen_ETFs):
    ETFs_dict = {}
    if type(choosen_ETFs) == str:
        I_need_this_variable_as_list = []
        I_need_this_variable_as_list.append(choosen_ETFs)
        choosen_ETF_symbols = [pobierz_do_spacji(choosen_ETF) for choosen_ETF in I_need_this_variable_as_list]
    else:
        choosen_ETF_symbols = [pobierz_do_spacji(choosen_ETF) for choosen_ETF in choosen_ETFs]

    choosen_ETF_tickers = [yfinance.Ticker(choosen_ETF_symbol) for choosen_ETF_symbol in choosen_ETF_symbols]

    for i, ETF in enumerate(choosen_ETF_symbols):
        ETFs_dict[choosen_ETF_tickers[i]] = ETF
    fig = px.line(title='Wartość jednostki ETF od jego powstania')
    for ETF in choosen_ETF_tickers:
        ETF_df = ETF.history(period='max')['Close']
        ETF_df = ETF_df.reset_index()
        ETF_df['Date'] = ETF_df['Date'].dt.date
        fig.add_scatter(x=ETF_df['Date'], y=ETF_df['Close'], mode='lines', name=ETFs_dict[ETF])

    fig.update_xaxes(
        dtick='M12',
        tickformat='%Y',
        tickmode='linear'
    )
    fig.update_layout(
        height=600,
        yaxis_title='Wartość jednostki w $'
    )
    return fig

@callback(
    Output('ETF_information_container', 'children'),
    [Input('my_input', 'value')]
)
def display_ETF_informations_boxes(choosen_ETFs):
    if type(choosen_ETFs) == str:
        ETF_ticker = pobierz_do_spacji(choosen_ETFs)
        ETF_informations = create_ETF_information_dict(ETF_ticker)
        fig_sectors = px.pie(ETF_informations['Sectors'], values='Percentage', names='Sector')
        fig_sectors.update_layout(width=500, height=500)
        fig_countries = px.pie(ETF_informations['Countries'], values='Percentage', names='Country')
        fig_countries.update_layout(width=500, height=500)
        return (html.Div([
                    html.H4(children=f'{choosen_ETFs}', style={'marginLeft': 50}),
                    html.Div(id=choosen_ETFs, children=[
                    html.Div(id='basic_informations', children=[
                        html.P(children='Podstawowe informacje:',  style={'textAlign': 'center', 'fontSize': 22}),
                        html.Div(f'Segment: {ETF_informations.get('Segment')}'),
                        html.Div(f'Category: {ETF_informations.get('Category')}'),
                        html.Div(f'Niche: {ETF_informations.get('Niche')}'),
                        html.Div(f'Focus: {ETF_informations.get('Focus')}'),
                        html.Div(f'Całkowity procentowy wzrost: {ETF_informations.get('Value increase')}'),
                        html.Div(f'Czas funkcjonowania (lata): {ETF_informations.get('Years')}'),
                        html.P(children='Wzrost:', style={'textAlign': 'center', 'fontSize': 22}),
                        dash_table.DataTable(data=ETF_informations.get('Returns').to_dict('records'),
                                             style_table={'width': '200px'}, style_header={'display': 'none'})
                    ]),
                    html.Div(id='basic_structure_informations', children=[
                        html.P(children='Struktura:', style={'textAlign': 'center', 'fontSize': 22}),
                        dash_table.DataTable(data=ETF_informations.get('Holdings structure').to_dict('records'),
                                             style_table={'width': '200px'}, style_header={'display': 'none'}),
                        dash_table.DataTable(data=ETF_informations.get('Companies_capitalization_structure').to_dict('records'),
                                             style_table={'width': '200px'}, style_header={'display': 'none'})
                    ]),
                    html.Div(id='top 10 holdings', children=[
                        html.P(children='TOP 10 firm:', style={'textAlign': 'center', 'fontSize': 22}),
                        dash_table.DataTable(data=ETF_informations['Top 10 holdings'].to_dict('records'), style_table={'width': '170px'})
                    ]),
                    html.Div(id='sectors chart', children=[
                        html.P(children='Ekspozycja na sektory gospodarki:', style={'textAlign': 'center', 'fontSize': 22}),
                        dcc.Graph(figure=fig_sectors)
                    ]),
                    html.Div(id='countries chart', children=[
                        html.P(children='Ekspozycja na rynki w krajach:', style={'textAlign': 'center', 'fontSize': 22}),
                        dcc.Graph(figure=fig_countries)
                    ])
                ], style={'display': 'flex', 'justify-content': 'space-around', 'align-items': 'center'})
            ]))
    else:
        ETF_informations_divs =  []
        for ETF in choosen_ETFs:
            ETF_ticker = pobierz_do_spacji(ETF)
            ETF_informations = create_ETF_information_dict(ETF_ticker)
            fig_sectors = px.pie(ETF_informations['Sectors'], values='Percentage', names='Sector')
            fig_sectors.update_layout(width=500, height=500)
            fig_countries = px.pie(ETF_informations['Countries'], values='Percentage', names='Country')
            fig_countries.update_layout(width=500, height=500)
            new_ETF_div =  (html.Div([
                html.H4(children=f'{ETF}', style={'marginLeft': 50}),
                html.Div(id=ETF, children=[
                    html.Div(id='basic_informations', children=[
                        html.P(children='Podstawowe informacje:', style={'textAlign': 'center', 'fontSize': 22}),
                        html.Div(f'Segment: {ETF_informations.get('Segment')}'),
                        html.Div(f'Category: {ETF_informations.get('Category')}'),
                        html.Div(f'Niche: {ETF_informations.get('Niche')}'),
                        html.Div(f'Focus: {ETF_informations.get('Focus')}'),
                        html.Div(f'Całkowity procentowy wzrost: {ETF_informations.get('Value increase')}'),
                        html.Div(f'Czas funkcjonowania (lata): {ETF_informations.get('Years')}'),
                        html.P(children='Wzrost:', style={'textAlign': 'center', 'fontSize': 22}),
                        dash_table.DataTable(data=ETF_informations.get('Returns').to_dict('records'),
                                             style_table={'width': '200px'}, style_header={'display': 'none'})
                    ]),
                    html.Div(id='basic_structure_informations', children=[
                        html.P(children='Struktura:', style={'textAlign': 'center', 'fontSize': 22}),
                        dash_table.DataTable(data=ETF_informations.get('Holdings structure').to_dict('records'),
                                             style_table={'width': '200px'}, style_header={'display': 'none'}),
                        dash_table.DataTable(
                            data=ETF_informations.get('Companies_capitalization_structure').to_dict('records'),
                            style_table={'width': '200px'}, style_header={'display': 'none'})
                    ]),
                    html.Div(id='top 10 holdings', children=[
                        html.P(children='TOP 10 firm:', style={'textAlign': 'center', 'fontSize': 22}),
                        dash_table.DataTable(data=ETF_informations['Top 10 holdings'].to_dict('records'),
                                             style_table={'width': '170px'})
                    ]),
                    html.Div(id='sectors chart', children=[
                        html.P(children='Ekspozycja na sektory gospodarki:', style={'textAlign': 'center', 'fontSize': 22}),
                        dcc.Graph(figure=fig_sectors)
                    ]),
                    html.Div(id='countries chart', children=[
                        html.P(children='Ekspozycja na rynki w krajach:', style={'textAlign': 'center', 'fontSize': 22}),
                        dcc.Graph(figure=fig_countries)
                    ])
                ], style={'display': 'flex', 'justify-content': 'space-around', 'align-items': 'center'})
            ]))
            ETF_informations_divs.append(new_ETF_div)
        return ETF_informations_divs

if __name__ == '__main__':
    app.run()
