# -*- coding: utf-8 -*-
"""
Web-interface for the facility location problem with streamlit.

@author: Christian Ruf
"""
import math
import pydeck as pdk
import streamlit as st
from pulp import LpStatusOptimal

from src.model.facility_location_model import Solution, Instance, Model


# %%

def get_map(solution: Solution):
    sites = solution.instance.sites
    customers = solution.instance.customers
    flows = solution.flows
    scaling_factor = 10000

    # Customer layer
    customers['radius'] = customers['demand'].map(lambda a: math.pow(a / 2.0 / math.pi, 0.5))  # area = 2πr²
    customer_layer = pdk.Layer(
        'ScatterplotLayer',
        customers,
        auto_highlight=True,
        opacity=0.9,
        stroked=True,
        filled=True,
        get_position=['lon', 'lat'],  # 1st value = longitude column header
        get_radius='radius',  # radius is given in meters
        radius_scale=scaling_factor,
        get_fill_color=[180, 0, 200, 140],  # RGBA value
    )

    # Sites layer
    sites['radius'] = sites['volume'].map(lambda a: math.pow(a / 2.0 / math.pi, 0.5))
    site_layer = pdk.Layer(
        'ScatterplotLayer',
        sites,
        auto_highlight=True,
        opacity=0.9,
        stroked=True,
        filled=True,
        get_position=['lon', 'lat'],
        get_radius='radius',
        radius_scale=scaling_factor,
        get_fill_color=[18, 49, 255],
    )

    # Flow layer
    flow_layer = pdk.Layer(
        'LineLayer',
        flows,
        opacity=0.9,
        getWidth='units',
        widthUnits='meters',
        widthScale=scaling_factor * 0.1,
        getSourcePosition=['from_lon', 'from_lat'],
        getTargetPosition=['to_lon', 'to_lat'],
        getColor=[180, 0, 200, 140],
    )

    # Set the viewport location
    view_state = pdk.ViewState(
        longitude=customers['lon'].mean(),
        latitude=customers['lat'].mean(),
        zoom=2,
        min_zoom=1,
        max_zoom=10,
        pitch=4.5,
        bearing=0)

    # Combined all of it and render a viewport
    deck = pdk.Deck(layers=[flow_layer, customer_layer, site_layer], initial_view_state=view_state,
                    map_style='mapbox://styles/mapbox/light-v9')

    # deck.to_html('deck-example.html')  # does not show map only markers
    return deck


# %%
st.title('Facility Location Problem')

# sidebar
n_customers = st.sidebar.slider('Number of customers',
                                min_value=1,
                                max_value=100,
                                value=50,
                                step=1)
demand_range = st.sidebar.slider('Demand range (uniform distributed)',
                                 min_value=1,
                                 max_value=100,
                                 value=(20, 80),
                                 step=10)
n_sites = st.sidebar.slider('Number of facilities',
                            min_value=1,
                            max_value=10,
                            value=5,
                            step=1)
capacity_range = st.sidebar.slider('Capacity range (uniform distributed)',
                                   min_value=1,
                                   max_value=5000,
                                   value=(1000, 4000),
                                   step=100)
fixed_cost_range = st.sidebar.slider('Fixed cost range (uniform distributed)',
                                     min_value=0,
                                     max_value=10000000,
                                     value=(4000000, 6000000),
                                     step=1000000)
cost_per_unit_mile = st.sidebar.slider('Shipping cost per unit and mile',
                                       min_value=0.0,
                                       max_value=10.0,
                                       value=0.1,
                                       step=0.1)
gap = st.empty()  # Add a placeholder

if st.sidebar.button('Optimize'):
    print('Generate instance')
    instance = Instance.generate(n_customers, demand_range,
                                 n_sites, capacity_range, fixed_cost_range,
                                 cost_per_unit_mile / 1.609344)
    print('Optimize')
    model = Model(instance)
    status, msg = model.solve()
    if status != LpStatusOptimal:
        st.write(msg)
    else:
        solution = model.get_solution()
        plt = get_map(solution)
        st.pydeck_chart(plt)

        st.header(f"Optimization results")
        md = """ 
        |Metric |Value | 
        |-|-|
        |Total costs|%.0f|
        |Total fixed costs|%.0f|
        |Total variable costs|%.0f|
        """ % (solution.value, solution.fixed_costs, solution.variable_costs)
        st.markdown(md)

        st.header(f"Sites ({len(solution.instance.sites)})")
        st.write(instance.sites.drop(columns=['loc', 'radius']).reset_index(drop=True))

        st.header(f"Customers ({len(solution.instance.customers)})")
        st.write(instance.customers.drop(columns=['loc', 'radius']).reset_index(drop=True))

# / siderbar
