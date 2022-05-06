from dash import Dash, dcc, html, Input, Output
from dash.exceptions import PreventUpdate
import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import pandas as pd
import geopandas as gpd
from ast import literal_eval
import re
import s3fs
import requests
import netCDF4
import xarray as xr
from shapely import wkt
from shapely.geometry import Point, Polygon
from rgb import *

import time

app_start = time.time()

page_start = time.time()

csv_load_start = time.time()
storm_dataset = pd.read_csv('data/storm_data_opt.csv', dtype={'lon': np.float64,
														'lat': np.float64,
														'n1': np.float64,
														'e1': np.float64,
														's1': np.float64,
														'w1': np.float64,
														'n2': np.float64,
														'e2': np.float64,
														's2': np.float64,
														'w2': np.float64})
csv_load_end = time.time()
print(f'Page load: import dataset csv: \n\t{csv_load_end - csv_load_start}')

# storm_dataset['m1_window'] = storm_dataset['m1_window'].apply(wkt.loads)
# storm_dataset['m2_window'] = storm_dataset['m2_window'].apply(wkt.loads)

# storm_gpd = gpd.GeoDataFrame(storm_dataset)
storm_list = storm_dataset['storm_name'].unique()
fs = s3fs.S3FileSystem(anon=True)

app = Dash(__name__, external_stylesheets=[dbc.themes.SLATE])

pio.templates.default = "plotly_dark"

s3fs_connect_start = time.time()
fs.open("s3://noaa-goes16/ABI-L2-MCMIPM/2021/241/14/OR_ABI-L2-MCMIPM1-M6_G16_s20212411400278_e20212411400347_c20212411400421.nc")
s3fs_connect_end = time.time()
print(f'Page load: s3fs open connection: \n\t{s3fs_connect_end - s3fs_connect_start}')

def make_empty_fig():
    figure = go.Figure()
    figure.layout.height = 300
    return figure
    
# def make_loading_fig():
#     fig = go.Figure()
# #     fig.layout.height = 10 
# #     fig.layout.width = 10
# #     fig.layout.paper_bgcolor='rgba(0,0,0,0)'
# #     fig.layout.plot_bgcolor='rgba(0,0,0,0)' 
#     fig.update_xaxes(visible=False).update_yaxes(visible=False)
# #     fig.update_layout(autosize=False)
#     return fig

###################################################### Layout

app.layout = html.Div([
	html.Br(),
	html.H3('Hurricane Satellite Imagery Browser', style={'textAlign': 'center', 'color': 'white'}),
# 	html.H4('Atlantic Hurricanes: 2021', style={'textAlign': 'center', 'color': 'white'}),
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
					value='Hurricane Elsa',
					options=[{'label': f'{storm_name} (2021)', 'value': storm_name}
								for storm_name in storm_list],
								clearable=False,
				)),
				]), width=3),
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
				]), width=6),

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
					dbc.Spinner(
						dcc.Graph(
						style={
							'height': '30vh'},
							id='map-graph',
							figure=make_empty_fig(),
							responsive=True,
							config={
								'modeBarButtonsToRemove': [
									'zoom',
									'pan',
									'select2d',
									'lasso2d'
									],
								'toImageButtonOptions': {
									'height': 500,
									'width': 500
									},
								'scrollZoom': False,
								'displaylogo': False
								}),
					delay_hide=8, color='primary'),
				]),
				html.Br(),
				dbc.Row([
					html.Br(),
					dbc.Label('Infrared Reflectance',
						style={
							'text-align': 'left',
							'color': 'white',
							'text-transform': 'uppercase'
							}),
					html.Br(),
					dbc.Spinner(dcc.Graph(style={'height': '30vh'}, id='3d-graph',
								figure=make_empty_fig(), responsive=True,
								config={'modeBarButtonsToRemove': ['orbitRotation',
																'tableRotation',
																'resetCameraLastSave3d'],
										'toImageButtonOptions': {'height': 500,
																'width': 500},
										'scrollZoom': False,
										'displaylogo': False}), delay_hide=8, color='primary'),
					html.Br(),
				]),

			], md=3, lg=3),

			dbc.Col([
				dbc.Label('Storm Imagery',
						style={'text-align': 'center',
								'color': 'white',
								'text-transform': 'uppercase'}),
				html.Br(),
				dcc.Store(id='rgb-store'), 
				html.Div(id='output'),
				dbc.Spinner(dcc.Graph(style={'height': '67vh'},id='image-graph', 
							figure=make_empty_fig(), responsive=True,
								config={'modeBarButtonsToRemove': ['zoom', 'pan'],
										'toImageButtonOptions': {'format':'svg', 'scale': 4},
										'scrollZoom': False,
										'displaylogo': False}), delay_hide=4, color='primary'),

			], md=6, lg=6),
			
			dbc.Col([
				dbc.Row([
					html.Br(),
					html.Br(),
					dbc.Label('Choose RGB Mode',
							style={'text-align': 'left',
									'color': 'white',
									'text-transform': 'uppercase'}),
					html.Br(),
					dcc.RadioItems(
						id='rgb-selector',
						options=[' Natural Color',
								 ' Enhanced IR',
								 ' (Day) Cloud Convection',
								 ' (Day) Convection',
								 ' (Day) Cloud Phase',
								 ' Air Mass',
								 ' Water Vapor',
								 ' Differential Water Vapor'],
						value=' Natural Color',
						labelStyle={'display': 'block'}
					),
# 				html.Br(),
				]),
				html.Br(),
				dbc.Row([
				html.Br(),
					dbc.Label('Download Options',
							style={'text-align': 'left',
									'color': 'white',
									'text-transform': 'uppercase'}),
					html.Br(),
					html.Button("Download PNG", id="btn-download-png"),
					dcc.Download(
						id='download-png')
				]),
				
				html.Br(),
				dbc.Row([

					html.Br(),
					html.Button("Download JPG", id="btn-download-jpg"),
					dcc.Download(
						id='download-jpg')
				]),

				html.Br(),
				dbc.Row([

					html.Br(),
					html.Button("Download netCDF Data", id="btn-download-netcdf"),
					dcc.Download(
						id='download-netcdf')
				]),
		
			], md=2, lg=2),
		]),
	]), color = 'dark', style={"height": "100vh"}),
    

	html.Br(),

], style={'backgroundColor': 'black'})

page_end = time.time()
print(f'Total page load and layout: \n\t{page_end - page_start}\n')

###################################################### Callbacks

@app.callback(
	Output('map-graph', 'figure'),
	Output('3d-graph', 'figure'),
	Output('image-graph', 'className'),
	Output('rgb-store', 'data'),
	Output('output','children'),
	Input('storm-dropdown', 'value'),
	Input('time-slider', 'value'),
)
	
def update_graphs(storm_name, selected_time):
	plotting_start = time.time()
	if not storm_name:
		raise PreventUpdate
		
	data_setup_start = time.time()
	df = storm_dataset[storm_dataset['storm_name'].eq(storm_name)].reset_index(drop=True)
	data_setup_end = time.time()
	print(f'Graphing: data setup: \n\t{data_setup_end - data_setup_start}')
				
	map_calc_start = time.time()
	location = Point((df['lon'][selected_time:selected_time+1]),
					 (df['lat'][selected_time:selected_time+1]))
					 
	n1 = df['n1'][selected_time]
	e1 = df['e1'][selected_time]
	s1 = df['s1'][selected_time]
	w1 = df['w1'][selected_time]
	n2 = df['n2'][selected_time]
	e2 = df['e2'][selected_time]
	s2 = df['s2'][selected_time]
	w2 = df['w2'][selected_time]
					 
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
	
# 	m1_window = df['m1_window'][selected_time]					 
# 	m2_window = df['m2_window'][selected_time]
	
	map_fig_start = time.time()
	map_fig = go.Figure()
	map_fig.add_trace(go.Scattergeo(
				name='Window 1',
				lon = (e1, e1, w1, w1, e1),
				lat = (n1, s1, s1, n1, n1),
				mode = 'lines',
				line = dict(
					color = 'purple'),
				fill = 'toself'))
				
	map_fig.add_trace(go.Scattergeo(
				name='Window 2',
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
					size = 8, 
					color = 'white', 
					symbol = '200'),
				opacity = 0.8))
	map_fig_end = time.time()
	print(f'Graphing: map figure creation: \n\t{map_fig_end - map_fig_start}')

	if location.within(m1_window):	
	
		map_calc_end = time.time()
		print(f'Graphing: map calculations: \n\t{map_calc_end - map_calc_start}')
		
		s3fs_m1_start = time.time()
		m1 = fs.open(fs.glob(f'{df.m1_combined[selected_time]}*.nc')[0])
		s3fs_m1_end = time.time()
		print(f'Graphing: s3fs mesoscale 1 load: \n\t{s3fs_m1_end - s3fs_m1_start}')

		xarray_read_start = time.time()
		m1_data = xr.load_dataset(m1)
		xarray_read_end = time.time()
		print(f'Graphing: xarray read time: \n\t{xarray_read_end - xarray_read_start}')
				
		surface_start = time.time()
		surface_fig = go.Figure(go.Surface(x=m1_data.x,y=m1_data.y,z=m1_data.CMI_C13,
								 showlegend=False, showscale=False,
								 colorscale='ice_r')
		)
		surface_end = time.time()
		print(f'Graphing: surface plot: \n\t{surface_end - surface_start}')
		
		color_plot_start = time.time()
		rgb = {
			' Natural Color': px.imshow(
				m1_data.rgb.NaturalColor(gamma=0.9, night_IR=True))
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' Enhanced IR': px.imshow(
				m1_data.CMI_C13, color_continuous_scale=ColorizedIR(), aspect='equal')
				.update_coloraxes(showscale=False)
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange=True),
			' (Day) Cloud Convection': px.imshow(
				m1_data.rgb.DayCloudConvection())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' (Day) Convection': px.imshow(
				m1_data.rgb.DayConvection())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' (Day) Cloud Phase': px.imshow(
				m1_data.rgb.DayCloudPhase())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' Air Mass': px.imshow(
				m1_data.rgb.AirMass())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' Water Vapor': px.imshow(
				m1_data.rgb.WaterVapor())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' Differential Water Vapor': px.imshow(
				m1_data.rgb.DifferentialWaterVapor())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
		}
		
		color_plot_end = time.time()
		print(f'Graphing: color plots to memory: \n\t{color_plot_end - color_plot_start}')
		
	elif location.within(m2_window):
	
		s3fs_m2_start = time.time()
		m2 = fs.open(fs.glob(f'{df.m2_combined[selected_time]}*.nc')[0])
		s3fs_m2_end = time.time()
		print(f'Graphing: s3fs mesoscale 2 load: \n\t{s3fs_m2_end - s3fs_m2_start}')

		xarray_read_start = time.time()
		m2_data = xr.load_dataset(m2)
		xarray_read_end = time.time()
		print(f'Graphing: xarray read time: \n\t{xarray_read_end - xarray_read_start}')
		
		surface_start = time.time()	
		surface_fig = go.Figure(go.Surface(x=m2_data.x,y=m2_data.y,z=m2_data.CMI_C13,
								 showlegend=False, showscale=False,
								 colorscale='ice_r')
		)
		surface_end = time.time()
		print(f'Graphing: surface plot: \n\t{surface_end - surface_start}')
		
		color_plot_start = time.time()
		rgb = {
			' Natural Color': px.imshow(
				m2_data.rgb.NaturalColor(gamma=0.9, night_IR=True))
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' Enhanced IR': px.imshow(
				m2_data.CMI_C13, color_continuous_scale=ColorizedIR(), aspect='equal')
				.update_coloraxes(showscale=False)
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange=True),
			' (Day) Cloud Convection': px.imshow(
				m2_data.rgb.DayCloudConvection())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' (Day) Convection': px.imshow(
				m2_data.rgb.DayConvection())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' (Day) Cloud Phase': px.imshow(
				m2_data.rgb.DayCloudPhase())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' Air Mass': px.imshow(
				m2_data.rgb.AirMass())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' Water Vapor': px.imshow(
				m2_data.rgb.WaterVapor())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
			' Differential Water Vapor': px.imshow(
				m2_data.rgb.DifferentialWaterVapor())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed'),
		}
		
		color_plot_end = time.time()
		print(f'Graphing: color plots to memory: \n\t{color_plot_end - color_plot_start}')

	else:
	
		s3fs_m1_start = time.time()
		m1 = fs.open(fs.glob(f'{df.m1_combined[selected_time]}*.nc')[0])
		s3fs_m1_end = time.time()
		print(f'Graphing: s3fs mesoscale 1 load: \n\t{s3fs_m1_end - s3fs_m1_start}')

		xarray_read_start = time.time()
		m1_data = xr.load_dataset(m1)
		xarray_read_end = time.time()
		print(f'Graphing: xarray read time: \n\t{xarray_read_end - xarray_read_start}')
		
		surface_fig = go.Figure(go.Surface(x=m1_data.x,y=m1_data.y,z=m1_data.CMI_C13,
								 showlegend=False, showscale=False,
								 colorscale='ice_r')
		)

		rgb = {
			' Natural Color': px.imshow(
				m1_data.rgb.NaturalColor(gamma=0.9, night_IR=True))
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed')
				.add_annotation(
					x=0.5,
					y=0.5,
					text=f'No Mesoscale Image<br>of {storm_name}<br>at This Time',
					xref='paper',
					yref='paper',
					showarrow=False,
					font_size=30,
					font_color='cyan', 
					bordercolor="gray",
					bgcolor="gray",
					opacity=0.8),
					
			' Enhanced IR': px.imshow(
				m1_data.CMI_C13,
				color_continuous_scale=ColorizedIR(),
				aspect='equal')
				.update_coloraxes(showscale=False)
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange=True)
				.add_annotation(
					x=0.5,
					y=0.5,
					text=f'No Mesoscale Image<br>of {storm_name}<br>at This Time',
					xref='paper',
					yref='paper',
					showarrow=False,
					font_size=30,
					font_color='cyan', 
					bordercolor="gray",
					bgcolor="gray",
					opacity=0.8),
					
			' (Day) Cloud Convection': px.imshow(
				m1_data.rgb.DayCloudConvection())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed')
				.add_annotation(
					x=0.5,
					y=0.5,
					text=f'No Mesoscale Image<br>of {storm_name}<br>at This Time',
					xref='paper',
					yref='paper',
					showarrow=False,
					font_size=30,
					font_color='cyan', 
					bordercolor="gray",
					bgcolor="gray",
					opacity=0.8),

			' (Day) Convection': px.imshow(
				m1_data.rgb.DayConvection())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed')
				.add_annotation(
					x=0.5,
					y=0.5,
					text=f'No Mesoscale Image<br>of {storm_name}<br>at This Time',
					xref='paper',
					yref='paper',
					showarrow=False,
					font_size=30,
					font_color='cyan', 
					bordercolor="gray",
					bgcolor="gray",
					opacity=0.8),

			' (Day) Cloud Phase': px.imshow(
				m1_data.rgb.DayCloudPhase())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed')
				.add_annotation(
					x=0.5,
					y=0.5,
					text=f'No Mesoscale Image<br>of {storm_name}<br>at This Time',
					xref='paper',
					yref='paper',
					showarrow=False,
					font_size=30,
					font_color='cyan', 
					bordercolor="gray",
					bgcolor="gray",
					opacity=0.8),

			' Air Mass': px.imshow(
				m1_data.rgb.AirMass())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed')
				.add_annotation(
					x=0.5,
					y=0.5,
					text=f'No Mesoscale Image<br>of {storm_name}<br>at This Time',
					xref='paper',
					yref='paper',
					showarrow=False,
					font_size=30,
					font_color='cyan', 
					bordercolor="gray",
					bgcolor="gray",
					opacity=0.8),

			' Water Vapor': px.imshow(
				m1_data.rgb.WaterVapor())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed')
				.add_annotation(
					x=0.5,
					y=0.5,
					text=f'No Mesoscale Image<br>of {storm_name}<br>at This Time',
					xref='paper',
					yref='paper',
					showarrow=False,
					font_size=30,
					font_color='cyan', 
					bordercolor="gray",
					bgcolor="gray",
					opacity=0.8),

			' Differential Water Vapor': px.imshow(
				m1_data.rgb.DifferentialWaterVapor())
				.update_layout(margin=dict(l=10, r=10, b=10, t=10))
				.update_traces(hovertemplate=None, hoverinfo='skip')
				.update_xaxes(visible=False)
				.update_yaxes(visible=False, autorange='reversed')
				.add_annotation(
					x=0.5,
					y=0.5,
					text=f'No Mesoscale Image<br>of {storm_name}<br>at This Time',
					xref='paper',
					yref='paper',
					showarrow=False,
					font_size=30,
					font_color='cyan', 
					bordercolor="gray",
					bgcolor="gray",
					opacity=0.8),
		}

	map_fig.update_geos(projection_type="orthographic",
					showcoastlines=False,
					landcolor='#212121',
					framecolor='#20324f',
					showocean=True,
					showlakes=True,
					lakecolor='#20324f',
					oceancolor='#20447a',
					projection_rotation=dict(
						lon=df['lon'][selected_time],
						lat=df['lat'][selected_time]
						))
	
	map_fig.update_layout(margin=dict(l=10, r=10, b=10, t=10), height=300)
	map_fig.update_traces(hovertemplate=None, hoverinfo='skip')
			
	surface_fig.update_layout(
					autosize=True,
					dragmode = 'turntable',
					margin=dict(l=10, r=10, b=10, t=10),
					height=300,
					scene_xaxis_showticklabels=False,
					scene_yaxis_showticklabels=False,
					scene_zaxis_showticklabels=False,
					scene_xaxis_showaxeslabels=False,
					scene_yaxis_showaxeslabels=False,
					scene_zaxis_showaxeslabels=False,
					scene_zaxis_autorange='reversed',
					scene_camera_eye_x=0,
					scene_camera_eye_y=-0.01,
					scene_camera_eye_z=1.75,
	)
	surface_fig.update_traces(hovertemplate=None, hoverinfo='skip')
	
	plotting_end = time.time()
	print(f'Total graphing time: \n\t{plotting_end - plotting_start}\n')

	return map_fig, surface_fig, dash.no_update, rgb, dash.no_update
	
@app.callback(
	Output('image-graph', 'figure'),
	Input('rgb-store', 'data'),
	Input('rgb-selector', 'value')	
)
	
def update_rgb(rgb, rgb_selection):
	rgb_update_start = time.time()
	if not rgb:
		raise PreventUpdate
	
	fig = rgb[rgb_selection]

	return fig

@app.callback(
	Output('download-png', 'data'),
	Input('btn-download-png', 'n_clicks'),
	prevent_initial_call=True,
)		

def func(n_clicks):
	return dcc.Graph(id='image-graph').write_image('test.png')
	
@app.callback(
	Output('download-jpg', 'data'),
	Input('btn-download-jpg', 'n_clicks'),
	prevent_initial_call=True,
)		

def func(n_clicks):
	return dcc.Graph(id='image-graph').write_image('test.jpg')

@app.callback(
	Output('download-netcdf', 'data'),
	Input('btn-download-netcdf', 'n_clicks'),
	prevent_initial_call=True,
)		

def func(n_clicks):
	return dcc.Graph(id='image-graph').write_image('test.png')


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
	app.run_server(debug=True)
	