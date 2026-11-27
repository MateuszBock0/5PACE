import plotly.graph_objects as go
from chart_theme import style_chart,reference_marker,rival_marker,heatmap_colors,role_colors,tokens

def test_dark_reference_and_rival_styles_preserve_chart_data():
    f=go.Figure()
    f.add_trace(go.Scatter(x=[3],y=[2],customdata=[["AIT-VISTA"]],mode="markers+text",marker=reference_marker("dark")))
    f.add_trace(go.Scatter(x=[3.1],y=[2.1],customdata=[["P1"]],mode="markers",marker=rival_marker("Research / emerging entrant","dark"),error_x={"array":[.2],"arrayminus":[0],"symmetric":False}))
    style_chart(f,"dark")
    assert f.layout.plot_bgcolor=="#141F30"
    assert f.data[0].marker.size==36 and f.data[1].marker.size==12
    assert f.data[1].marker.opacity==1 and f.data[1].marker.line.width>=1.5
    assert f.data[1].marker.symbol=="diamond"
    assert f.data[0].customdata[0][0]=="AIT-VISTA" and f.data[1].customdata[0][0]=="P1"
    assert tuple(f.data[1].x)==(3.1,) and tuple(f.data[1].error_x.array)==(.2,)

def test_heatmap_hit_targets_and_statuses_preserved():
    f=go.Figure(go.Scatter(x=[0],y=[0],mode="markers+text",marker={"symbol":"square","size":36,"opacity":.01},text=["?"]))
    style_chart(f,"dark")
    assert f.data[0].marker.opacity==.01
    assert f.data[0].text==("?",)
    assert len(set(heatmap_colors("dark").values()))==8
    assert heatmap_colors("dark")["Unknown"]!=heatmap_colors("dark")["Unassessed"]
    assert role_colors("dark")["Direct visual AIT candidate"]!=role_colors("dark")["Research / emerging entrant"]

def test_chart_style_light_fallback_and_line_markers():
    f=go.Figure(go.Scatter(x=[1,2],y=[3,4],mode="lines+markers",line={"dash":"dot"}))
    style_chart(f,"light")
    assert f.layout.plot_bgcolor==tokens("light")["plot"]
    assert f.data[0].line.dash=="dot" and f.data[0].marker.size==8
