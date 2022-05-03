from dash import Dash, dcc, html, Input, Output
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import pandas as pd
import re
import s3fs
import requests
import netCDF4
import xarray as xr
from shapely.geometry import Point, Polygon
from rgb import *

storm_dataset = pd.read_csv('data/storm_data.csv')
storm_list = storm_dataset['storm_name'].unique()
fs = s3fs.S3FileSystem(anon=True)

app = Dash(__name__, external_stylesheets=[dbc.themes.SLATE])

pio.templates.default = "plotly_dark"

def make_empty_fig():
    fig = go.Figure()
    fig.layout.height = 300
    return fig

app.layout = html.Div([
	html.H3('Storm Satellite Imagery Browser', style={'textAlign': 'center', 'color': 'white'}),
	html.H4('Atlantic Hurricanes: 2021', style={'textAlign': 'center', 'color': 'white'}),
	html.Br(),
	
    dbc.Card(
        dbc.CardBody([
			dbc.Row([
				dbc.Col(html.Div([
					dbc.Label('Choose a Storm',
						style={'text-align': 'center',
								'color': 'white',
								'text-transform': 'uppercase'}),
					html.Br(),
					html.Div(dcc.Dropdown(id='storm-dropdown',
					value='Hurricane Sam',
					options=[{'label': storm_name, 'value': storm_name}
								for storm_name in storm_list],
								clearable=False,
				)),
				]), width=4),
				dbc.Col(html.Div([
					dbc.Label('Choose an Image (Drag the Slider)',
						style={'text-align': 'center',
								'color': 'white',
								'text-transform': 'uppercase'}),
					html.Br(),
					dcc.Slider(id='time-slider',
						min=0,
						max=0,
						value=0,
					)
				]), width=8),

			], align='center'), 
	html.Br(),
	
		dbc.Row([
			dbc.Col([
				dbc.Row([
					dbc.Label('Mesoscale Windows',
							style={'text-align': 'left',
									'color': 'white',
									'text-transform': 'uppercase'}),
					html.Br(),
					dcc.Loading(dcc.Graph(style={'height': '23vh'}, id='map-graph',
								figure=make_empty_fig(), responsive=True,
								config={'modeBarButtonsToRemove': ['zoom', 'pan'],
										'toImageButtonOptions': {'height': 500,
																'width': 500},
										'scrollZoom': False,
										'displaylogo': False}), type='circle')
				]),
				dbc.Row([
					dbc.Label('Infrared Reflectance',
							style={'text-align': 'left',
									'color': 'white',
									'text-transform': 'uppercase'}),
					html.Br(),
					dcc.Loading(dcc.Graph(style={'height': '23vh'}, id='3d-graph',
								figure=make_empty_fig(), responsive=True,
								config={'modeBarButtonsToRemove': ['orbitRotation',
																'tableRotation',
																'resetCameraLastSave3d'],
										'toImageButtonOptions': {'height': 500,
																'width': 500},
										'scrollZoom': False,
										'displaylogo': False}), type='circle')
				]),
				dbc.Row([
					dbc.Label('Choose RGB Mode',
							style={'text-align': 'left',
									'color': 'white',
									'text-transform': 'uppercase'}),
					html.Br(),
					dcc.RadioItems(
						id='rgb-selector',
						options=['Natural Color',
								 'Enhanced IR',
								 'Day Cloud Convection',
								 'Day Convection',
								 'Day Cloud Phase',
								 'Air Mass',
								 'Water Vapor',
								 'Differential Water Vapor'],
						value='Natural Color',
						labelStyle={'display': 'block'}
					),
				]),
			], md=4, lg=4),

			dbc.Col([
				dbc.Label('Storm Imagery',
						style={'text-align': 'center',
								'color': 'white',
								'text-transform': 'uppercase'}),
				html.Br(),
				dcc.Loading(dcc.Graph(style={'height': '70vh'},id='image-graph', 
							figure=make_empty_fig(),
								config={'modeBarButtonsToRemove': ['zoom', 'pan'],
										'toImageButtonOptions': {'height': 800,
																'width': 800},
										'scrollZoom': False,
										'displaylogo': False}), type='circle')
			], md=8, lg=8),
		]),
	]), color = 'dark', style={"height": "100vh"}),
    

	html.Br(),

], style={'backgroundColor': 'black'})


@app.callback(
	Output('map-graph', 'figure'),
	Output('3d-graph', 'figure'),
	Output('image-graph', 'figure'),
	Input('storm-dropdown', 'value'),
	Input('time-slider', 'value'),
	Input('rgb-selector', 'value')
)
	
def update_graphs(storm_name, selected_time, rgb_selection):
	if not storm_name:
		raise PreventUpdate

	df = storm_dataset[storm_dataset['storm_name'].eq(storm_name)].reset_index(drop=True)
	m1 = fs.open(fs.glob(f'{df.m1_combined[selected_time]}*.nc')[0])
	m2 = fs.open(fs.glob(f'{df.m2_combined[selected_time]}*.nc')[0])
	
	with xr.open_dataset(m1) as m1_data:
		n1 = m1_data.geospatial_lat_lon_extent.attrs['geospatial_northbound_latitude']
		e1 = m1_data.geospatial_lat_lon_extent.attrs['geospatial_eastbound_longitude']
		s1 = m1_data.geospatial_lat_lon_extent.attrs['geospatial_southbound_latitude']
		w1 = m1_data.geospatial_lat_lon_extent.attrs['geospatial_westbound_longitude']
		
		with xr.open_dataset(m2) as m2_data:
			n2 = m2_data.geospatial_lat_lon_extent.attrs['geospatial_northbound_latitude']
			e2 = m2_data.geospatial_lat_lon_extent.attrs['geospatial_eastbound_longitude']
			s2 = m2_data.geospatial_lat_lon_extent.attrs['geospatial_southbound_latitude']
			w2 = m2_data.geospatial_lat_lon_extent.attrs['geospatial_westbound_longitude']
			
			location = Point(df['lon'][selected_time:selected_time+1],
							 df['lat'][selected_time:selected_time+1])
							 
			m1_window = Polygon([(e1, n1),
								 (e1, s1),
								 (w1, s1),
								 (w1, n1),
								 (e1, n1)])
								 
			m2_window = Polygon([(e2, n2),
								 (e2, s2),
								 (w2, s2),
								 (w2, n2),
								 (e2, n2)])

			map_fig = go.Figure()
			map_fig.add_trace(go.Scattergeo(
						name='Mesoscale 1',
						lon = (e1, e1, w1, w1, e1),
						lat = (n1, s1, s1, n1, n1),
						mode = 'lines',
						line = dict(
							color = 'purple'),
						fill = 'toself'))
						
			map_fig.add_trace(go.Scattergeo(
						name='Mesoscale 2',
						lon = (e2, e2, w2, w2, e2),
						lat = (n2, s2, s2, n2, n2),
						mode = 'lines',
						line = dict(
							color = 'orange'),
						fill = 'toself'))

			map_fig.add_trace(go.Scattergeo(
						name='Storm Path',
						lon = df['lon'],
						lat = df['lat'],
						mode = 'lines', 
						line = dict(
							width = 1, 
							color = 'white'),
						opacity = 0.8))

			map_fig.add_trace(go.Scattergeo(
						name=storm_name,
						lon = df['lon'][selected_time:selected_time+1],
						lat = df['lat'][selected_time:selected_time+1],
						mode = 'markers', 
						marker = dict(
							size = 10, 
							color = 'white', 
							symbol = '200'),
						opacity = 0.8))
			
			if location.within(m1_window):			
				surface_fig = go.Figure(go.Surface(x=m1_data.x,y=m1_data.y,z=m1_data.CMI_C13,
										 showlegend=False, showscale=False,
										 colorscale='ice')
				)

				rgb = {
					'Natural Color': px.imshow(m1_data.rgb.NaturalColor(night_IR=True, gamma=1.1)),
					'Enhanced IR': ColorizedIR(m1_data),
					'Day Cloud Convection': px.imshow(m1_data.rgb.DayCloudConvection()),
					'Day Convection': px.imshow(m1_data.rgb.DayConvection()),
					'Day Cloud Phase': px.imshow(m1_data.rgb.DayCloudPhase()),
					'Air Mass': px.imshow(m1_data.rgb.AirMass()),
					'Water Vapor': px.imshow(m1_data.rgb.WaterVapor()),
					'Differential Water Vapor': px.imshow(m1_data.rgb.DifferentialWaterVapor()),
				}
				image_fig = rgb[rgb_selection]
				
			elif location.within(m2_window):	
				surface_fig = go.Figure(go.Surface(x=m2_data.x,y=m2_data.y,z=m2_data.CMI_C13,
										 showlegend=False, showscale=False,
										 colorscale='ice')
				)

				rgb = {
					'Natural Color': px.imshow(m2_data.rgb.NaturalColor(gamma=1.1, night_IR=True)),
					'Enhanced IR': ColorizedIR(m2_data),
					'Day Cloud Convection': px.imshow(m2_data.rgb.DayCloudConvection()),
					'Day Convection': px.imshow(m2_data.rgb.DayConvection()),
					'Day Cloud Phase': px.imshow(m2_data.rgb.DayCloudPhase()),
					'Air Mass': px.imshow(m2_data.rgb.AirMass()),
					'Water Vapor': px.imshow(m2_data.rgb.WaterVapor()),
					'Differential Water Vapor': px.imshow(m2_data.rgb.DifferentialWaterVapor()),
				}
				image_fig = rgb[rgb_selection]

			else:
				surface_fig = go.Figure(go.Surface(x=m1_data.x,y=m1_data.y,z=m1_data.CMI_C13,
										 showlegend=False, showscale=False,
										 colorscale='ice')
				)

				rgb = {
					'Natural Color': px.imshow(m1_data.rgb.NaturalColor(gamma=1.1, night_IR=True)),
					'Enhanced IR': ColorizedIR(m1_data),
					'Day Cloud Convection': px.imshow(m1_data.rgb.DayCloudConvection()),
					'Day Convection': px.imshow(m1_data.rgb.DayConvection()),
					'Day Cloud Phase': px.imshow(m1_data.rgb.DayCloudPhase()),
					'Air Mass': px.imshow(m1_data.rgb.AirMass()),
					'Water Vapor': px.imshow(m1_data.rgb.WaterVapor()),
					'Differential Water Vapor': px.imshow(m1_data.rgb.DifferentialWaterVapor()),
				}
				image_fig = rgb[rgb_selection]
				
				image_fig.add_annotation(x=0.5, y=0.5, text=f'No Mesoscale Image<br>of {storm_name}<br>at This Time',
										 xref='paper', yref='paper', showarrow=False,
										 font_size=30, font_color='cyan', 
										 bordercolor="gray", bgcolor="gray", opacity=0.8)


			map_fig.update_geos(projection_type="orthographic",
							showcoastlines=False,
							landcolor='#373a3c',
							framecolor='#0c2230',
			                showocean=True,
			                showlakes=True,
			                lakecolor='#0c2230',
			                oceancolor='#0c2230',
							projection_rotation=dict(
								lon=df['lon'].median(),
								lat=df['lat'].median()))
			
			map_fig.update_layout(margin=dict(l=10, r=10, b=10, t=10),
							height=300
			)
					
			surface_fig.update_layout(
							autosize=True,
							dragmode = 'turntable',
							margin=dict(l=10, r=10, b=10, t=10),
							height=300,
							scene_xaxis_showticklabels=False,
							scene_yaxis_showticklabels=False,
							scene_xaxis_showaxeslabels=False,
							scene_yaxis_showaxeslabels=False,
							scene_zaxis_showaxeslabels=False,
			)

			image_fig.update_layout(margin=dict(l=10, r=10, b=10, t=10)
			)
			image_fig.update_xaxes(visible=False).update_yaxes(visible=False)


		return map_fig, surface_fig, image_fig
		

@app.callback(
	[Output('time-slider', 'min'),
	Output('time-slider', 'max'),
	Output('time-slider', 'value')],
	Input('storm-dropdown', 'value')
)

def update_slider(storm_name):
	df = storm_dataset[storm_dataset['storm_name'].eq(storm_name)].reset_index(drop=True)
	min=df.index.min()
	max=df.index.max()
	value=df.index.min()

	return min, max, value

if __name__ == '__main__':
	app.run_server()
