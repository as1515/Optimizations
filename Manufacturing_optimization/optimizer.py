import pandas as pd
from cplex import Cplex

# sales_data - Index(['xitem', 'xdesc', 'xqty', 'xval', 'xlineamt'], dtype='object')
# finished_raw_data - Index(['goods', 'raw', 'xqty/unit', 'xrate'], dtype='object')
# raw rate - Index(['raw', 'xrate'], dtype='object')
class RawMaterialProcurementOptimizer:
    def __init__(self, finished_raw_data, sales_data, raw_rate ,budget):
        self.finished_raw_data = finished_raw_data
        self.sales_data = sales_data
        self.raw_rate = raw_rate
        self.budget = budget
        
        # load all the products sold and average sales qty
        self.products = self.sales_data['xitem'].unique()
        self.average_sales = dict(zip(self.sales_data['xitem'], self.sales_data['xqty']))

        # load raw materials relations 
        self.raw_materials = self.raw_rate['raw'].unique()
        self.raw_material_cost = dict(zip(self.raw_rate['raw'], self.raw_rate['xrate']))

        self.problem = Cplex()
        self.problem.set_problem_type(Cplex.problem_type.LP)
        self.problem.objective.set_sense(self.problem.objective.sense.minimize)

        # Decision 
        self.raw_material_vars = {material: self.problem.variables.add(
            names=[f"x_{material}"], lb=[0], ub=[float('inf')])[0] for material in self.raw_materials}

        self._setup_objective()
        self._setup_constraints()

    def _setup_objective(self):

        cost_coefficients = [self.raw_material_cost[material] for material in self.raw_materials]
        variable_indices = [self.raw_material_vars[material] for material in self.raw_materials]

        # minimize cost
        self.problem.objective.set_linear(zip(variable_indices, cost_coefficients))

    def _setup_constraints(self):

        for product in self.products:
            required_materials = self.finished_raw_data[self.finished_raw_data['goods'] == product]
            product_demand = self.average_sales[product]

            for material in self.raw_materials:
                required_units = required_materials[material].values[0] * product_demand
                if required_units > 0:
                    self.problem.linear_constraints.add(
                        lin_expr=[[list(self.raw_material_vars.values()), [required_units]]],
                        senses=['G'],
                        rhs=[required_units],
                        names=[f"Demand_Constraint_{product}_{material}"]
                    )

        # Add budget constraint
        total_cost_expr = [self.raw_material_cost[material] * self.raw_material_vars[material] for material in self.raw_materials]
        self.problem.linear_constraints.add(
            lin_expr=[[list(self.raw_material_vars.values()), list(self.raw_material_cost.values())]],
            senses=['L'],
            rhs=[self.budget],
            names=["Budget_Constraint"]
        )

    def solve(self):
        """Solve the optimization problem and return the results."""
        self.problem.solve()

        # Extract solution values
        solution = {}
        for material in self.raw_materials:
            index = self.raw_material_vars[material]
            solution[material] = self.problem.solution.get_values(index)
        
        return solution, self.problem.solution.get_objective_value()

    def display_results(self):
        """Display the results of the optimization."""
        solution, total_cost = self.solve()
        print("Optimal Quantities of Raw Materials to Purchase:")
        for material, quantity in solution.items():
            print(f"{material}: {quantity}")
        print(f"Total Cost: {total_cost}")

