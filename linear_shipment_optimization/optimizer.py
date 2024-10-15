
import pandas as pd
import numpy as np
from cplex import Cplex
from cplex.callbacks import SimplexCallback
from cplex.exceptions import CplexSolverError

class ShipmentOptimizer:
    def __init__(self, data_file):
        self.data_file = data_file
        self.products = None
        self.budget_constraint = None
        self.cbm_constraint = None
        self.weight_constraint = None
        self.problem = Cplex()
        self.objective_values = []
    
    def load_data(self):
        df = pd.read_excel(self.data_file, engine='openpyxl')
        self.products = df.set_index('Code').T.to_dict()

    def set_constraints(self, budget, cbm, weight):
        self.budget_constraint = budget
        self.cbm_constraint = cbm
        self.weight_constraint = weight
    
    def setup_problem(self):
        self.problem.set_problem_type(Cplex.problem_type.LP)
        self.problem.objective.set_sense(self.problem.objective.sense.maximize)
        
        product_ids = list(self.products.keys())
        variable_names = [f"x_{pid}" for pid in product_ids]
        profits = [self.products[pid]['Profit/unit'] * self.products[pid]['Demand/month'] for pid in product_ids] #decision variable 
        
        lb = [self.products[pid]['MOQ/unit'] for pid in product_ids]  
        ub = [float('inf') for _ in product_ids]  

        # check and filter out invalid values from profit, lb and ub)
        valid_indices = [i for i in range(len(profits)) 
                        if np.isfinite(profits[i]) and np.isfinite(lb[i])]

        variable_names = [variable_names[i] for i in valid_indices]
        profits = [profits[i] for i in valid_indices]
        lb = [lb[i] for i in valid_indices]
        ub = [ub[i] for i in valid_indices]
        
        print("Variable Names:", variable_names)
        print("Profits:", profits)
        print("Lower Bounds (lb):", lb)
        print("Upper Bounds (ub):", ub)

        self.problem.variables.add(obj=profits, lb=lb, ub=ub, names=variable_names)
        
        # Add constraints
        prices = [self.products[pid]['Price/unit'] for pid in product_ids]
        self.problem.linear_constraints.add(
            lin_expr=[[variable_names, prices]],
            senses=['L'],
            rhs=[self.budget_constraint],
            names=["Budget_Constraint"]
        )
        
        cbms = [self.products[pid]['CBM/unit'] for pid in product_ids]
        self.problem.linear_constraints.add(
            lin_expr=[[variable_names, cbms]],
            senses=['L'],
            rhs=[self.cbm_constraint],
            names=["CBM_Constraint"]
        )
        
        weights = [self.products[pid]['Weight/unit'] for pid in product_ids]
        self.problem.linear_constraints.add(
            lin_expr=[[variable_names, weights]],
            senses=['L'],
            rhs=[self.weight_constraint],
            names=["Weight_Constraint"]
        )
    
    # solve iteratively - eliminate lowest profit item and repeat
    def solve_iteratively(self): 
        class ObjectiveSimplexCallback(SimplexCallback):
            def __call__(self):
                self.model.objective_values.append(self.get_objective_value())

        self.problem.register_callback(ObjectiveSimplexCallback)
        ObjectiveSimplexCallback.model = self

        relaxation_factor = 0.9

        while True:
            try:
                self.problem.solve()
                solution_values = self.problem.solution.get_values()
                total_profit = self.problem.solution.get_objective_value()

                result = {
                    "total_profit": total_profit,
                    "product_quantities":{
                        pid: solution_values[i] for i,pid in enumerate(self.products.keys())
                    }
                }

                return result
            except CplexSolverError:
                #if infeasiblility detected remove lowest profit item and if no solution
                if not self.products:
                    raise Exception("No feasible solution could be found with the given constraints.")
             
                lowest_profit_item = min(
                    self.products, 
                    key=lambda pid: self.products[pid]['Profit/unit'] * self.products[pid]['Demand/month']
                )

                del self.products[lowest_profit_item]

                self.problem = Cplex()

                #remove invalid
                self.products = {pid: data for pid, data in self.products.items() 
                            if pd.notna(data['Profit/unit']) and pd.notna(data['MOQ/unit'])}

                if not self.products:
                    raise Exception("No valid products left to optimize.")
                self.setup_problem()

    # for manual work, I need a non-iterative process. 
    def solve(self):
        
        class ObjectiveProgressCallback(SimplexCallback):
            def __call__(self):
                obj_val = self.get_objective_value()
                self.model.objective_values.append(obj_val)

        callback_instance = self.problem.register_callback(ObjectiveProgressCallback)
        callback_instance.model = self  
        
        self.problem.solve()
        solution_values = self.problem.solution.get_values()
        total_profit = self.problem.solution.get_objective_value()
        
        result = {
            "total_profit": total_profit,
            "product_quantities": {
                pid: solution_values[i] for i, pid in enumerate(self.products.keys())
            }
        }
        return result

    def save_results_to_excel(self, result, output_file):
        product_ids = list(result['product_quantities'].keys())
        quantities = list(result['product_quantities'].values())
        total_costs = [quantities[i] * self.products[pid]['Price/unit'] for i, pid in enumerate(product_ids)]
        total_profits = [quantities[i] * self.products[pid]['Profit/unit'] for i, pid in enumerate(product_ids)]

        df = pd.DataFrame({
            'Product Code': product_ids,
            'Suggested Quantity': quantities,
            'Price per Unit': [self.products[pid]['Price/unit'] for pid in product_ids],
            'Total Cost': total_costs,
            'Profit per Unit': [self.products[pid]['Profit/unit'] for pid in product_ids],
            'Total Profit': total_profits
        })

        totals_row = {
            'Product Code': 'Total',
            'Suggested Quantity': sum(quantities),
            'Price per Unit': '',
            'Total Cost': sum(total_costs),
            'Profit per Unit': '',
            'Total Profit': sum(total_profits)
        }
        df = df.append(totals_row, ignore_index=True)

        df.to_excel(output_file, index=False)