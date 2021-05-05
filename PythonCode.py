import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from uk_covid19 import Cov19API
import dash_bootstrap_components as dbc
#from urllib.request import urlopen
#import json



###########################################################################################################
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
###########################################################################################################

#Basic access from UK Covid 19 API
#Can find how to do access and run the API here: https://publichealthengland.github.io/coronavirus-dashboard-api-python-sdk/pages/getting_started.html
lowertierla = ['areaType=ltla']

df = {
    'date':'date',
    'Area' : 'areaName',
    'Code' : 'areaCode',
    'Cases' : 'newCasesBySpecimenDateRollingSum',
    'Rate' : 'newCasesBySpecimenDateRollingRate',
    'Percentage' : 'newCasesBySpecimenDateChangePercentage'
    }

df2 = {
    'Area' : 'areaName',
    'CasesLastWeek' : 'newCasesBySpecimenDateRollingSum'
    }

latest = {'newCasesBySpecimenDateRollingSum' : 'newCasesBySpecimenDateRollingSum'}

api_map = Cov19API(filters = lowertierla, structure = df, latest_by = latest)

d_map = api_map.get_dataframe()

###########################################################################################################

#Date manipulation to get the data from 7 days before the last update 
from datetime import datetime, timedelta

date_latest = datetime.strptime(d_map['date'][0], '%Y-%m-%d')
date_lastweek = date_latest - timedelta(days = 7)
date_lastweek = date_lastweek.strftime("%Y-%m-%d")
date_latest = date_latest.strftime('%d %b %Y')

lastweek = ['date={}'.format(date_lastweek), 'areaType=ltla']

api_maplast = Cov19API(filters = lastweek, structure = df2)
d_maplast = api_maplast.get_dataframe()


#Just to merge the last week data to latest data, to be able to calculate absolute/percentage difference to last
d_map = d_map.merge(d_maplast, how='left', on='Area')
d_map['CaseDiff'] = d_map['Cases'] - d_map['CasesLastWeek']
d_map['CasePercDiff'] = d_map['CaseDiff']/d_map['CasesLastWeek']

for i in range(len(d_map)-1):
    if d_map['CasePercDiff'][i] == float('inf'):
        d_map.loc[i,'CasePercDiff'] = d_map['Cases'][i]-1

#Set rate to discrete bins, so that the map can be coloured discretely rather than continuous
bins = [-1, 0, 10, 50, 100, 200, 400, 800, 100000]
labels2 = ['Missing Data', '0-9', '10-49', '50-99', '100-199', '200-399', '400-799', '800+']

#Creating this discrete factor by creating a copy of the continuous Rate variable
d_map['Rate2'] = pd.cut(d_map.Rate, bins, labels = labels2)

###########################################################################################################

#Lower tier local authority map file on ONS
#with urlopen("https://opendata.arcgis.com/datasets/b7fc294e5c8643f5b506acc2122c6880_0.geojson") as response:
#    ltlamap = json.load(response)
    
#This is too memory intensive, so use online map shaper to reduce specificity of the map
  
ltlamap = pd.read_json(r'C:\Users\epayne.esure\Downloads\Local_Authority_Districts__April_2019__UK_BGC.json')
ltlamapsep = ltlamap['features'].to_list()

ltlamapsingle = {'type' : 'FeatureCollection',
          'features' : ltlamapsep}

lookup = {feature['properties']['LAD19CD']: feature for feature in ltlamapsingle['features']}

###########################################################################################################

#Function to get map file for selected authority (the one that has been clicked on)
def get_highlights(selections):
    geojson_highlights = dict()
    for k in ltlamapsingle.keys():
        if k != 'features':
            geojson_highlights[k] = ltlamapsingle[k]
        else:
            geojson_highlights[k] = [lookup[selection] for selection in selections]        
    return geojson_highlights

def get_figure(selections):
    # Base map layer
    fig = px.choropleth_mapbox(d_map, locations="Code", hover_data=dict({'Rate2':False, 'Code':False}), color_discrete_map={
                        'Missing Data': '#FFFFFF',
                        '0-9' : '#EBCE15',
                        '10-49' : '#77DE5F',
                        '50-99' : '#58C4A0',
                        '100-199' : '#4A84BA',
                        '200-399' : '#314FA8',
                        '400-799' : '#512E8C',
                        '800+' : '#260C36'}, category_orders={
                      'Rate2' : [
                          'Missing Data',
                          '0-9',
                          '10-49',
                          '50-99',
                          '100-199',
                          '200-399',
                          '400-799',
                          '800+'
                      ]
                    }, featureidkey="properties.LAD19CD", 
                            geojson=ltlamapsingle, color="Rate2", opacity=0.5)

    # Second layer
    if len(selections) > 0:
        # highlights contain the geojson information for only selected authority
        
        highlights = get_highlights(selections)

        for i in range(d_map.Rate2.nunique()):
            
            fig.add_trace(
                px.choropleth_mapbox(d_map, geojson=highlights, 
                                 color="Rate2",
                                 locations="Code", color_discrete_map={
                        'Missing Data': '#FFFFFF',
                        '0-9' : '#EBCE15',
                        '10-49' : '#77DE5F',
                        '50-99' : '#58C4A0',
                        '100-199' : '#4A84BA',
                        '200-399' : '#314FA8',
                        '400-799' : '#512E8C',
                        '800+' : '#260C36'}, category_orders={
                      'Rate2' : [
                          'Missing Data',
                          '0-9',
                          '10-49',
                          '50-99',
                          '100-199',
                          '200-399',
                          '400-799',
                          '800+'
                      ]
                    }, hover_data=dict({'Rate2':False, 'Code':False}), hover_name=None,
                                 featureidkey="properties.LAD19CD",                              
                                 opacity=1).data[i]
                )

    #------------------------------------#   
    fig.update_traces(hoverinfo=None)
    fig.update_layout(mapbox_style="carto-positron", showlegend=False,
                      mapbox_zoom=6, height=900,
                      mapbox_center={"lat": 55, "lon": 0},
                      margin={"r":0,"t":0,"l":0,"b":0},
                      uirevision='constant')
    
    return fig

def get_card(selections):
    row = d_map[d_map['Code'] == selections]
    row = row.reset_index(drop = True)
    if selections == '':
        card_content1a = []
        return card_content1a
    
    name = row['Area'][0]
    
    if row['Rate2'][0] == 'Missing Data':
        card_content1a = [
            dbc.CardBody([
                html.Div(html.H2("{}".format(name))),
                html.Br(),
                html.Div(html.H4("Data missing."))])]
        
        return card_content1a
        
    cases = row['Cases'][0]
    rate = row['Rate'][0]
    number = row['CaseDiff'][0]
    percnumber = row['CasePercDiff'][0]
    
    if number > 0:
        case_change = dbc.Button("\u2191" + "{}".format(number) + "\u3000" + "({:.1%})".format(percnumber), color="danger", disabled=True)
    if number == 0:
        case_change = dbc.Button("\u2192" + "{}".format(number) + "\u3000" + "({:.1%})".format(percnumber), color="success", disabled=True)
    if number < 0:
        case_change = dbc.Button("\u2193" + "{}".format(number) + "\u3000" + "({:.1%})".format(percnumber), color="success", disabled=True)
    
    card_content1a = [
        dbc.CardBody(
            [
                html.Div(html.H2("{}".format(name))),
                html.Br(),
                html.Div(html.H4("Total Cases")),
                html.Div([html.H3(["{} \u3000".format(cases), case_change])]), 
                html.Br(),
                html.Div(html.H4("Rolling Rate")),
                html.Div(html.H3("{}".format(rate)))

                ]
            ),
        ]   
    
    return card_content1a


badges = html.Div(
    [   
        dbc.Badge("Missing Data", color="light"),
        dbc.Badge("0-9", color="#EBCE15"),
        dbc.Badge("10-49", color="#77DE5F"),
        dbc.Badge("50-99", color="#58C4A0"),
        dbc.Badge("100-199", color="#4A84BA"),
        dbc.Badge("200-399", color="#314FA8"),
        dbc.Badge("400-799", color="#512E8C"),        
        dbc.Badge("800+", color="#260C36"),        
        
    ]
)


###########################################################################################################

app.layout = html.Div([
    
    html.H2("Interactive Map", style={'text-align':'left'}),
    html.H5("Browse cases data for specific areas at Local Tier Local Authorities (LTLA) within the UK."),
    html.H5("The map displays weekly data, which are updated everyday."),
    html.H5("Seven–day rolling rate of new cases by specimen date ending on {}".format(date_latest)),
    
    badges,

    dbc.Row(
        [
            dbc.Col(dcc.Graph(id='choropleth', figure={}), width = 7),
            dbc.Col(dbc.Card(id='info', children={}, color="light"))
        ]
    ),
    
    html.Br(),
    html.Br(),
    html.H6("Contains MSOA names © Open Parliament copyright and database right 2019/2020"),
    html.H6("Contains Ordnance Survey data © Crown copyright and database right 2019/2020"),
    html.H6("Contains Royal Mail data © Royal Mail copyright and database right 2019/2020"),
    html.H6("Contains Public Health England data © Crown copyright and database right 2019/2020"),   
    html.H6("Office for National Statistics licensed under the Open Government Licence v.3.0"), 
        
     ])

###########################################################################################################

@app.callback(
    [Output('choropleth', 'figure'),
     Output('info', 'children')],
    [Input('choropleth', 'clickData')])
def update_figure(clickData):
    selections = set()
    
    if clickData is not None:            
        location = clickData['points'][0]['location']
        selections.add(location)
        return get_figure([location]), get_card(location)
                    
    return get_figure([]), get_card('')


if __name__ == '__main__':
    app.run_server(port=8080,debug=False)
