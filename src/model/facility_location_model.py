from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
import pulp

from src.model.util import get_random_us_locs, Loc

eps = 0.0001  # floating point tolerance


class Instance:

    @classmethod
    def generate(cls, n_customers, demand_range,
                 n_sites, capacity_range, fixed_cost_range,
                 shipping_cost):
        """
        Generate a random instance.

        :param n_customers: number of customers
        :param demand_range: pair with min and max demand
        :param n_sites: number of sites
        :param capacity_range: pair with min and max site-capacity
        :param fixed_cost_range: pair with min and max site-fixed cost
        :param shipping_cost: cost factor for shipping one unit one km
        :return: new instance
        """
        print('Generate instance')

        # Generate customers
        customers = get_random_us_locs(n_customers)
        customers.drop(columns=['pop'], inplace=True)
        customers['loc'] = customers[['lat', 'lon']].apply(lambda r: Loc(r[0], r[1]), axis=1)
        customers['demand'] = np.random.randint(low=demand_range[0],
                                                high=demand_range[1],
                                                size=n_customers)

        # Generate sites
        sites = get_random_us_locs(n_sites)
        sites.drop(columns=['pop'], inplace=True)
        if fixed_cost_range[0] == fixed_cost_range[1]:
            sites['fixed_cost'] = fixed_cost_range[0]
        else:
            sites['fixed_cost'] = np.random.randint(low=fixed_cost_range[0],
                                                    high=fixed_cost_range[1],
                                                    size=n_sites)
        sites['capacity'] = np.random.randint(low=capacity_range[0],
                                              high=capacity_range[1],
                                              size=n_sites)
        sites['loc'] = sites[['lat', 'lon']].apply(lambda r: Loc(r[0], r[1]), axis=1)

        return Instance(n_customers, customers, n_sites, sites, shipping_cost)

    def __init__(self, n_customers, customers, n_sites, sites, shipping_cost):
        assert type(n_customers) == int
        self.n_customers = n_customers
        self.customers = customers
        assert type(n_sites) == int
        self.n_sites = n_sites
        self.sites = sites
        self.shipping_cost = shipping_cost

    def __str__(self):
        return str(self.__dict__)


# %%

@dataclass
class Solution:
    instance: Instance
    status: int
    value: float
    secs: float
    xs: dict
    ys: dict
    flows: pd.DataFrame
    fixed_costs: float
    variable_costs: float


class Model(pulp.LpProblem):

    def __init__(self, instance: Instance):
        super().__init__('FacilityLocationProblem', pulp.LpMinimize)
        self.start = datetime.now()
        self.data = instance
        s_ids = range(self.data.n_sites)
        c_ids = range(self.data.n_customers)
        self.site_fixed_costs = self.data.sites['fixed_cost'].to_dict()
        self.site_capacities = self.data.sites['capacity'].to_dict()
        self.total_demand = self.data.customers['demand'].sum()
        self.total_capacity = self.data.sites['capacity'].sum()

        # Variables
        y = pulp.LpVariable.dicts(name='y',
                                  indexs=s_ids,
                                  cat=pulp.LpBinary)
        x = pulp.LpVariable.dicts(name='x',
                                  indexs=(s_ids, c_ids),
                                  lowBound=0, cat=pulp.LpContinuous)
        self.y, self.x = y, x

        # Objective function
        self.shipping_costs = {
            (i, j): self.data.shipping_cost * self.data.sites.loc[i, 'loc'].haversine_distance(
                self.data.customers.loc[j, 'loc'])
            for i in s_ids for j in c_ids}
        self += (pulp.lpSum([self.site_fixed_costs[i] * y[i] for i in s_ids])
                 + pulp.lpSum(
                    [self.shipping_costs[i, j] * x[i][j]
                     for i in s_ids for j in c_ids]))

        # Demand constraints
        for j in c_ids:
            self += pulp.lpSum([x[i][j] for i in s_ids]) \
                    >= self.data.customers.loc[j, 'demand'], f"demand_{j}"

        # Site capacity constraints
        for i in s_ids:
            self += pulp.lpSum([x[i][j] for j in c_ids]) \
                    <= min(self.site_capacities[i], self.total_demand) * y[i], f"capacity_{i}"

    def solve(self, timeout_sec=120):
        print('Solve model')
        if self.total_demand > self.total_capacity:
            return (pulp.LpStatusInfeasible,
                    f"Total demand ({self.total_demand}) exceeds total capacity ({self.total_capacity})")
        # super().writeLP(data_folder_path / "facility.lp")
        super().solve()

        status = self.status
        if status == pulp.LpStatusInfeasible:
            print("Model is infeasible")
            return status, f"Model is infeasible"
        elif status == pulp.LpStatusNotSolved:
            print("Model not optimal")
            return status, f"Model not solved to optimality"
        elif status == pulp.LpStatusOptimal:
            print("Model optimal")

        return status, "Model optimal"

    def get_solution(self) -> Solution:
        # Get variable values & create dictionaries
        yval = {i: self.y[i].varValue for i in range(self.data.n_sites) if self.y[i].varValue > eps}
        xval = {(i, j): self.x[i][j].varValue
                for i in range(self.data.n_sites) for j in range(self.data.n_customers)
                if self.x[i][j].varValue > eps}

        # Extend existing DateFrames
        self.data.sites['volume'] = self.data.sites.index.map(
            lambda x: sum([v for (i, j), v in xval.items() if i == x]))
        self.data.customers['volume'] = self.data.customers.index.map(
            lambda x: sum([v for (i, j), v in xval.items() if j == x]))

        # Create flows DataFrame
        flows = pd.DataFrame([(i, 'site', j, 'customer', v) for (i, j), v in xval.items()],
                             columns=['from', 'from_type', 'to', 'to_type', 'units'])
        flows['from_loc'] = flows['from'].map(lambda r: self.data.sites.loc[r, 'loc'])
        flows['from_lat'] = flows['from'].map(lambda r: self.data.sites.loc[r, 'loc'].lat)
        flows['from_lon'] = flows['from'].map(lambda r: self.data.sites.loc[r, 'loc'].lon)
        flows['to_loc'] = flows['to'].map(lambda r: self.data.customers.loc[r, 'loc'])
        flows['to_lat'] = flows['to'].map(lambda r: self.data.customers.loc[r, 'loc'].lat)
        flows['to_lon'] = flows['to'].map(lambda r: self.data.customers.loc[r, 'loc'].lon)

        total_fixed_costs = sum([self.site_fixed_costs[i] * yval[i] for i in yval])
        total_shipping_costs = sum([self.shipping_costs[i, j] * xval[i, j] for i, j in xval])
        return Solution(self.data, self.status, pulp.value(self.objective), (datetime.now() - self.start).seconds,
                        xval, yval, flows,
                        total_fixed_costs, total_shipping_costs)
