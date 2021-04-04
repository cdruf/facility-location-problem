# facility-location-problem

This project is an examplary implementation of the facility location problem. Features are

* the optimization model implemented with PuLP, and
* a dashboard implemented with streamlit and deck.gl.

## Optimization problem

The facility location problem can be outlined as follows. Given 

* a set of potential sites with fixed costs and capacities,
* a set of customers with demands, and 
* variable transportation cost, 
  
determine the flows of the product from sites to customers and a subset of sites such that customer demand is fullfilled minimizing the total costs (fixed site costs, variable shipping costs)

## Streamlit dashboard

Start streamlit with 

    streamlit run main_streamlit.py

A browser should open and the dashboard should load.
