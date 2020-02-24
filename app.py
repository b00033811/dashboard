from flask import Flask, render_template
from bokeh.embed import server_document
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Slider
from bokeh.plotting import figure
from bokeh.server.server import Server
from bokeh.themes import Theme
from tornado.ioloop import IOLoop
from bokeh.plotting import figure, output_file, show
from bokeh.plotting import ColumnDataSource
from redistimeseries.client import Client
from bokeh.layouts import column
from bokeh.models import HoverTool
from datetime import datetime
import pandas as pd

app = Flask(__name__)
redis_host='redis-cluster-ip-service'
redis_port='6379'
connection=Client(host=redis_host,port=redis_port)
def bkapp(doc):
    MSEC=1
    SEC=1*MSEC
    MIN=60*SEC
    rts=Client(host=redis_host,port=redis_port)
    def get_ts(name,_min=0,_max=-1):
        y=rts.range('Temperature', _min,_max, aggregation_type='avg', bucket_size_msec=5*MIN)
        y_time,y_value=zip(*y)
        y_time=[datetime.utcfromtimestamp(int(x)) for x in y_time]
        y_value=[v for v in y_value]
        dataset_y=dict(time=y_time,value=y_value)
        ds=ColumnDataSource(dataset_y)
        return ds
    def get_pred(name,_min=0,_max=-1):
        y=rts.range(name, _min,_max)

        y_time,y_value=zip(*y)
        y_time=[datetime.utcfromtimestamp(int(x)) for x in y_time]
        y_value=[v for v in y_value]
        dataset_y=dict(time=y_time,value=y_value)
        ds=ColumnDataSource(dataset_y)
        return ds
    def get_bounds(upper,lower,_min=0,_max=-1):
        y=rts.range(upper, _min,_max)
        y_time,y_upper=zip(*y)
        y=rts.range(lower, _min,_max)
        _,y_lower=zip(*y)
        y_time=[datetime.utcfromtimestamp(int(x)) for x in y_time]
        y_upper=[v for v in y_upper]
        y_lower=[v for v in y_lower]
        dataset_y=dict(time=y_time,y_upper=y_upper,y_lower=y_lower)
        ds=ColumnDataSource(dataset_y)
        return ds
    def draw_line(p,data,line_color=None,line_width=2,alpha=1):
        output_file("test.html")
        p.line(x='time',y='value',source=data,line_width=line_width,line_color=line_color,alpha=alpha)
        return p


    # we want to plot 3 axes and have a slider to manipulate the date range
    def make_plot(name,dim_x,dim_y,label_x,label_y,type_x="datetime",x_range=None,y_range=None,tools=None,hover=None):
        if x_range is None:
            p = figure(plot_width=dim_x,
            plot_height=dim_y,
            x_axis_label=label_x,
            y_axis_label=label_y,
            x_axis_type=type_x,
            tools=TOOLS)
            p.add_tools(hover)
            return  p
        else:
            p = figure(plot_width=dim_x,
            plot_height=dim_y,
            x_axis_label=label_x,
            y_axis_label=label_y,
            x_axis_type=type_x,
            x_range=x_range,
            tools=TOOLS)
            p.add_tools(hover)
            return  p
    dim_y=250
    dim_x=int(5*dim_y)
    TOOLS = "pan,wheel_zoom,help"
    hover=HoverTool(
        tooltips=[
            ( 'Date',   '@time{%F %H:%M}'            ),
            ( 'Value',  '@value' )
        ],

        formatters={
            'time'      : 'datetime', # use 'datetime' formatter for 'date' field
        },
    )
    p_temperature=make_plot(name="Temperature",
                            dim_x=dim_x,
                            dim_y=dim_y,
                            label_x="Time",
                            label_y="Temperature",
                            tools=TOOLS,
                            hover=hover)
    p_temperature.xaxis.visible = False

    p_trend=make_plot(name='Trend',
                        dim_x=dim_x,
                        dim_y=dim_y,
                        label_x="Time",
                        label_y="Trend",
                        x_range=p_temperature.x_range,
                        tools=TOOLS,
                        hover=hover)
    p_trend.xaxis.visible = False

    p_seasonality=make_plot(name="Daily Seasonality",
                            dim_x=dim_x,
                            dim_y=dim_y,
                            label_x="Time",
                            label_y="Daily Seasonality",
                            x_range=p_trend.x_range,
                            tools=TOOLS,
                            hover=hover)

    def draw_trend(p_trend):
        data=get_pred('trend')
        p_trend=draw_line(p_trend,data,line_color='#2171b5')

        data=get_pred('trend_upper')
        p_trend= draw_line(p_trend,data,line_color='#2171b5',alpha=0.5,line_width=1)    

        data=get_pred('trend_lower')
        p_trend= draw_line(p_trend,data,line_color='#2171b5',alpha=0.5,line_width=1) 

        bounds=get_bounds('trend_upper','trend_lower')
        patch=p_trend.varea(x='time',
            y1='y_upper',
            y2='y_lower',source=bounds,fill_alpha=0.2)
        patch.level = 'underlay'
        return p_trend
    def draw_seasonality(p_seasonality):
        data=get_pred('daily')
        return draw_line(p_seasonality,data,line_color='#2171b5')
    def draw_temperature(p_temperature):
        data=get_pred('yhat')
        p_temperature= draw_line(p_temperature,data,line_color='#2171b5')
        data=get_ts('Temperature')
        p_temperature.circle('time', 'value', size=2, color="black", alpha=0.25,source=data)

        data=get_pred('yhat_upper')
        p_temperature= draw_line(p_temperature,data,line_color='#2171b5',alpha=0.5,line_width=1)    

        data=get_pred('yhat_lower')
        p_temperature= draw_line(p_temperature,data,line_color='#2171b5',alpha=0.5,line_width=1) 

        bounds=get_bounds('yhat_upper','yhat_lower')
        patch=p_temperature.varea(x='time',
            y1='y_upper',
            y2='y_lower',source=bounds,fill_alpha=0.2)
        patch.level = 'underlay'
        return p_temperature

    p_trend=draw_trend(p_trend)
    p_seasonality=draw_seasonality(p_seasonality)
    p_temperature=draw_temperature(p_temperature)

    layout=column(p_temperature,p_trend,p_seasonality)


    doc.add_root(layout)

    # doc.theme = Theme(filename="theme.yaml")


@app.route('/', methods=['GET'])
def bkapp_page():
    script = server_document('http://localhost:5006/bkapp')
    return render_template("embed.html", script=script, template="Flask")


def bk_worker():
    # Can't pass num_procs > 1 in this configuration. If you need to run multiple
    # processes, see e.g. flask_gunicorn_embed.py
    server = Server({'/bkapp': bkapp}, io_loop=IOLoop(), allow_websocket_origin=["10.0.2.15:30037"])
    server.start()
    server.io_loop.start()

from threading import Thread
Thread(target=bk_worker).start()

if __name__ == '__main__':
    print('Opening single process Flask app with embedded Bokeh application on http://localhost:8001/')
    print()
    print('Multiple connections may block the Bokeh app in this configuration!')
    print('See "flask_gunicorn_embed.py" for one way to run multi-process')
    app.run(port=8001)