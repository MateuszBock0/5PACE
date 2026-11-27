from decision import customer_position,dataset_label,importance_lane,signals,observation_product
from test_command import comparison_fixture

def test_customer_axis_independent_and_negation():
    p={"Target Customers":"Marketed: spacecraft manufacturing and quality teams; named customers unverified."}
    assert customer_position(p,[])["Customer position"]=="Space AIT target segment"
    assert customer_position({"Target Customers":"No spacecraft manufacturing customers confirmed."},[])["Customer position"]=="Unresolved target overlap"
    dep={"Deployment ID":"d","Customer Organisation":"Synthetic","Industry":"Space hardware manufacturing","Use Case":"Assembly inspection","Deployment Status":"Reported implementation"}
    assert customer_position({},[dep])["Customer position"]=="Space AIT implementation case"
    assert customer_position({},[dep])["Procurement"].startswith("Unresolved")
    dep["Deployment Status"]="Research / demonstration"
    assert customer_position({},[dep])["Customer position"]=="Unresolved target overlap"

def test_modes_and_importance():
    assert dataset_label({}, "Synthetic UX fixture","a","a")=="SYNTHETIC UX PREVIEW"
    assert dataset_label({}, "Google Sheets","a","b")=="HISTORICAL LOCAL SNAPSHOT"
    assert dataset_label({}, "Google Sheets","a","a")=="LOCAL GOOGLE SHEETS SNAPSHOT"
    assert dataset_label({}, "Offline import","a","a")=="LOCAL IMPORTED SNAPSHOT"
    assert importance_lane({"command_profiles":{"c":{"customer_importance":"High"}}},"c")=="Unresolved"
    assert importance_lane({"command_profiles":{"c":{"customer_importance":"High","customer_importance_reference":"explicit reference"}}},"c")=="High"

def test_chart_route_preserves_product_criterion_and_reference():
    from founder_ui import chart_route
    class UI:
        session_state={}
    d=comparison_fixture()
    ui=UI()
    ui.session_state={"plot":{"selection":{"points":[{"customdata":["DEMO-P2","CR1"]}]}}}
    chart_route(ui,"plot",d,"criterion")
    assert ui.session_state["founder_workspace"]=="Competitor Explorer"
    assert ui.session_state["founder_company_pending"]=="DEMO-CO-2"
    assert ui.session_state["founder_product_pending"]=="DEMO-P2"
    assert ui.session_state["profile_criterion_pending"]=="CR1"
    assert ui.session_state["profile_section_pending"]=="Compare"
    ui.session_state={"plot":{"selection":{"points":[{"customdata":["DEMO-P1","DEMO-CO-1","Deployments","dep"]}]}}}
    chart_route(ui,"plot",d,"signal")
    assert ui.session_state["profile_reference_pending"]==("Deployments","dep")
    assert ui.session_state["profile_section_pending"]=="Deployments"
