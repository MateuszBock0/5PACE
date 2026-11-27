"""Presentation-only chart styling for the native Streamlit theme.

Do not change coordinates, categories, error bars, customdata or evidence.
Reference and competitor markers keep the established 36:12 hierarchy.
"""
import plotly.express as px
import streamlit as st

DARK={"background":"#101826","plot":"#141F30","text":"#E6EFFA","grid":"#33445B","outline":"#EAF2FC","reference":"#45E0CC","reference_fill":"rgba(69,224,204,0.16)","band":"#223249","hover":"#24354D"}
LIGHT={"background":"#FFFFFF","plot":"#F8FAFC","text":"#192A3B","grid":"#DFE7EF","outline":"#26384C","reference":"#087E7B","reference_fill":"rgba(8,126,123,0.18)","band":"#E9EEF2","hover":"#EAF1F8"}
DARK_COLORS=["#60A5FA","#FBBF55","#F472B6","#36D6A0","#B49AFF","#FF846D","#4DD6F2","#D0DE71","#B7C6DB","#C4A58C"]
LIGHT_COLORS=["#2563EB","#BA7608","#BE357D","#07865B","#7855C7","#CD4B34","#087F9F","#677C18","#69798C","#93694A"]
ROLES=["Direct visual AIT candidate","Workflow / procurement substitute candidate","Cross-industry competitor candidate","Enabling technology","Complementary system","Research / emerging entrant","Internal / custom solution","Historical solution","Unresolved role"]
ROLE_SYMBOLS=dict(zip(ROLES,["circle","square","triangle-up","hexagon","pentagon","diamond","triangle-down","cross","circle"]))
STATUS_NAMES=["Explicitly unsupported","Unassessed","Unknown","Disputed","Not applicable","Announced","Partially supported","Supported"]
STATUS_DARK=["#742D40","#2A3445","#425873","#65447D","#414A54","#264D85","#775221","#155E4B"]
STATUS_LIGHT=["#F3D5D5","#E9EEF2","#C8D6E3","#E5D6EF","#D9DCE1","#DBE5F9","#F8E8CD","#D9EEEA"]

def active_theme():
    # Honour the application's configured theme, not the browser's initial
    # OS preference (which may still be light during first render).
    return "light" if st.get_option("theme.base")=="light" else "dark"

def tokens(mode=None):
    return DARK if (mode or active_theme())=="dark" else LIGHT

def colors(mode=None):
    return DARK_COLORS if (mode or active_theme())=="dark" else LIGHT_COLORS

def role_colors(mode=None):
    return dict(zip(ROLES,colors(mode)))

def action_colors(mode=None):
    p=colors(mode)
    return {"React":p[5],"Benchmark":p[0],"Research":p[1],"Monitor":p[3]}

def heatmap_colors(mode=None):
    return dict(zip(STATUS_NAMES,STATUS_DARK if (mode or active_theme())=="dark" else STATUS_LIGHT))

def reference_marker(mode=None,symbol="circle"):
    t=tokens(mode)
    return {"symbol":symbol,"size":36,"color":t["reference_fill"],"line":{"color":t["reference"],"width":2.6},"opacity":1}

def rival_marker(role=None,mode=None):
    t=tokens(mode)
    marker={"size":12,"opacity":1,"line":{"color":t["outline"],"width":1.8}}
    if role in ROLES:
        marker.update(color=role_colors(mode)[role],symbol=ROLE_SYMBOLS[role])
    return marker

def style_chart(fig,mode=None):
    mode=mode or active_theme();t=tokens(mode);palette=colors(mode)
    fig.update_layout(template="plotly_dark" if mode=="dark" else "plotly_white",
                      paper_bgcolor=t["background"],plot_bgcolor=t["plot"],
                      font={"color":t["text"],"size":13},colorway=palette,
                      hoverlabel={"bgcolor":t["hover"],"font":{"color":t["text"],"size":13},"bordercolor":t["grid"]})
    fig.update_xaxes(gridcolor=t["grid"],zerolinecolor=t["grid"],linecolor=t["grid"],tickfont={"color":t["text"]})
    fig.update_yaxes(gridcolor=t["grid"],zerolinecolor=t["grid"],linecolor=t["grid"],tickfont={"color":t["text"]})
    fig.update_polars(bgcolor=t["plot"],radialaxis={"gridcolor":t["grid"],"linecolor":t["grid"]},angularaxis={"gridcolor":t["grid"],"linecolor":t["grid"]})
    default_map=dict(zip((c.lower() for c in px.colors.qualitative.Plotly),palette))
    def remap(c):
        return default_map.get(c.lower(),c) if isinstance(c,str) else c
    for trace in fig.data:
        typ=trace.type
        if typ not in ("scatter","scattergl","scatterpolar","bar"):continue
        marker=trace.marker
        # A deliberately invisible marker is the selectable heatmap hit area.
        if typ!="bar" and marker.opacity is not None and isinstance(marker.opacity,(int,float)) and marker.opacity<.05:
            continue
        if typ!="bar" and isinstance(marker.size,(int,float)) and marker.size==36:
            # Reference is explicitly drawn first by map builders.
            continue
        if isinstance(marker.color,str):marker.color=remap(marker.color)
        if typ!="bar" and getattr(trace,"line",None) is not None and isinstance(trace.line.color,str):
            trace.line.color=remap(trace.line.color)
        if typ=="bar":continue
        if "markers" in (trace.mode or ""):
            if marker.size is None:marker.size=8 if "lines" in trace.mode else 13
            elif isinstance(marker.size,(int,float)) and marker.size<12 and "lines" not in trace.mode:marker.size=12
            if marker.opacity is None:marker.opacity=1
            if marker.line.width is None or (isinstance(marker.line.width,(int,float)) and marker.line.width<1.5):marker.line.width=1.5
            if marker.line.color is None:marker.line.color=t["outline"]
        # Keep uncertainty intervals visible without altering their extent.
        for key in ("error_x","error_y"):
            err=getattr(trace,key,None)
            if err is not None and err.array is not None:
                err.color=t["text"];err.thickness=1.3;err.width=3
    return fig

def render_chart(container,fig,**kwargs):
    # We own the palette; avoid Streamlit replacing explicit Plotly defaults.
    return container.plotly_chart(style_chart(fig),theme=None,**kwargs)
