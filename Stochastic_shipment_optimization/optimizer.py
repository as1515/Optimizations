import pandas as pd
import cplex
import numpy as np
from cplex.exceptions import CplexError

# scenarios columns 
# Index(['Scenario', 'Probability', 'Product_Code', 'Demand/month',
#        'Total_Profit'],
#       dtype='object')

# shipment_stochastic columns 
# Index(['Code', 'Name', 'MOQ/unit', 'CBM/unit', 'Weight/unit', 'Price/unit'], dtype='object')

class StochasticOptimizer:
    def __init__(self, merged_data, budget_limit, cbm_limit, weight_limit, alpha):
        self.num_scenarios = merged_data['Scenario'].nunique()
        self.merged_data = merged_data
        self.products = self.merged_data['Product_Code'].unique()
        self.scenarios = self.merged_data['Scenario'].unique()
        self.prob = cplex.Cplex()
        self.var_names = []
        self.var_profit_coeffs = []
        self.budget_limit = budget_limit
        self.cbm_limit = cbm_limit
        self.weight_limit = weight_limit
        self.alpha = alpha

    def initialize_model(self):
        self.prob.set_problem_type(cplex.Cplex.problem_type.MILP)
        self.prob.objective.set_sense(self.prob.objective.sense.maximize)

    def create_decision_variables(self):
        for product_code in self.products:
            for scenario in self.scenarios:
                var_name = f"x_{product_code}_{scenario}"
                self.var_names.append(var_name)
                scenario_data_row = self.merged_data[
                    (self.merged_data['Product_Code'] == product_code) &
                    (self.merged_data['Scenario'] == scenario)
                ].iloc[0]

                # Profit coefficient calculation
                profit = scenario_data_row['Profit/unit'] * scenario_data_row['Demand/month']
                probability = scenario_data_row['Probability']
                profit_coefficient = profit * probability
                self.var_profit_coeffs.append(profit_coefficient)

        self.prob.variables.add(names=self.var_names, obj=self.var_profit_coeffs, types=['C'] * len(self.var_names))

    def add_constraints(self):
        budget_coeffs = []
        cbm_coeffs = []
        weight_coeffs = []
        
        for product_code in self.products:
            for scenario in self.scenarios:
                scenario_data_row = self.merged_data[
                    (self.merged_data['Product_Code'] == product_code) &
                    (self.merged_data['Scenario'] == scenario)
                ].iloc[0]
                probability = scenario_data_row['Probability']
                budget_coeffs.append(scenario_data_row['Price/unit'] * scenario_data_row['Demand/month'] * probability)
                cbm_coeffs.append(scenario_data_row['CBM/unit'] * scenario_data_row['Demand/month']* probability)
                weight_coeffs.append(scenario_data_row['Weight/unit'] * scenario_data_row['Demand/month']* probability)

                # budget_coeffs.append(scenario_data_row['Price/unit'] * scenario_data_row['Demand/month'] )
                # cbm_coeffs.append(scenario_data_row['CBM/unit'] * scenario_data_row['Demand/month'])
                # weight_coeffs.append(scenario_data_row['Weight/unit'] * scenario_data_row['Demand/month'])
        
        # Adding budget constraint
        self.prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(self.var_names, budget_coeffs)],
            senses=["L"],
            rhs=[self.budget_limit],
            names=["budget_constraint"]
        )

        # Adding CBM constraint
        self.prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(self.var_names, cbm_coeffs)],
            senses=["L"],
            rhs=[self.cbm_limit],
            names=["cbm_constraint"]
        )

        # Adding Weight constraint
        self.prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(self.var_names, weight_coeffs)],
            senses=["L"],
            rhs=[self.weight_limit],
            names=["weight_constraint"]
        )

        self.merged_data['MOQ/unit'] = self.merged_data['MOQ/unit'] * self.alpha
        # Adding MOQ Constraints
        for product_code in self.products:
            moq = self.merged_data[self.merged_data['Product_Code'] == product_code]['MOQ/unit'].iloc[0]
            product_vars = [var for var in self.var_names if product_code in var]
            coeffs = [1] * len(product_vars)
            self.prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(product_vars, coeffs)],
                senses=["G"],
                rhs=[moq],
                names=[f"moq_constraint_{product_code}"]
            )

        # for product_code in self.products:
        #     product_vars = [var for var in self.var_names if product_code in var]
        #     coeffs = [1] * len(product_vars)
            
        #     # Sum of all decision variables for this product across different scenarios should be <= 1
        #     self.prob.linear_constraints.add(
        #         lin_expr=[cplex.SparsePair(product_vars, coeffs)],
        #         senses=["L"],
        #         rhs=[1],
        #         names=[f"mutual_exclusivity_{product_code}"]
        #     )

    def solve_iteratively(self):
        #restart the interation with remaining products
        remaining_products = self.products.copy()  # Start with all products
        feasible_solution_found = False
        iteration = 0

        while not feasible_solution_found and len(remaining_products) > 0:
            print(f"Iteration {iteration}: Attempting to solve with {len(remaining_products)} products.")
            self.update_model(remaining_products)
            try:
                self.prob.solve()
                solution_status = self.prob.solution.get_status()

                if solution_status == cplex.callbacks.SolutionStatus.optimal:
                    feasible_solution_found = True
                    print("Feasible solution found!")
                    
                    self.export_solution()
                    break
                else:
                    print(f"No feasible solution in iteration {iteration}. Removing least profitable product.")
            except CplexError as e:
                print(f"Optimization error in iteration {iteration}: {e}")

            product_profits = {}
            #remove the product with the lowest profit. 
            for product in remaining_products:
                product_data = self.merged_data[self.merged_data['Product_Code'] == product]
                total_expected_profit = (product_data['Profit/unit'] * product_data['Demand/month'] * product_data['Probability']).sum()
                product_profits[product] = total_expected_profit

            least_profitable_product = min(product_profits, key=product_profits.get)
            print(f"Removing product {least_profitable_product} with expected profit {product_profits[least_profitable_product]}.")
            remaining_products = [p for p in remaining_products if p != least_profitable_product]
            iteration += 1

        if not feasible_solution_found:
            print("No feasible solution found after eliminating all products.")

    # update the model based on the remaining products 
    def update_model(self, remaining_products):
        self.prob = cplex.Cplex()  
        self.var_names = []
        self.var_profit_coeffs = []

        filtered_data = self.merged_data[self.merged_data['Product_Code'].isin(remaining_products)]
        self.products = filtered_data['Product_Code'].unique()
        self.scenarios = filtered_data['Scenario'].unique()

        self.__init__(filtered_data, self.budget_limit, self.cbm_limit, self.weight_limit, self.alpha)
        self.initialize_model()
        self.create_decision_variables()
        self.add_constraints()



    def solve(self):
        try:
            self.prob.parameters.mip.tolerances.mipgap.set(0.01)  # Set tolerance for solution quality
            self.prob.solve()
            print("Solution status:", self.prob.solution.get_status())
            print("Objective value (Maximum Profit):", self.prob.solution.get_objective_value())

            solution = self.prob.solution.get_values(self.var_names)
            selected_products = [self.var_names[i] for i in range(len(solution)) if solution[i] > 0.5]
            print("Selected Products and Scenarios:")
            for product_scenario in selected_products:
                print(product_scenario)

            solution_data = []
            total_cbm = 0
            total_weight = 0
            total_budget = 0

            for product_scenario in selected_products:
                split_data = product_scenario.split('_')
                product_code = '_'.join(split_data[1:-1])  # Handles cases like 'M-110'
                scenario = split_data[-1]

                scenario_data_row = self.merged_data[
                    (self.merged_data['Product_Code'] == product_code) &
                    (self.merged_data['Scenario'] == int(scenario))
                ].iloc[0]

                order_quantity = scenario_data_row['Demand/month']
                expected_profit = scenario_data_row['Profit/unit'] * order_quantity
                product_name = scenario_data_row['Name']
                probability = scenario_data_row['Probability']
                moq = scenario_data_row['MOQ/unit']

                total_cbm += scenario_data_row['CBM/unit'] * order_quantity * probability
                total_weight += scenario_data_row['Weight/unit'] * order_quantity * probability
                total_budget += scenario_data_row['Price/unit'] * order_quantity * probability

                if order_quantity < scenario_data_row['MOQ/unit']:
                    print(f"Product {product_code} does not satisfy MOQ. Selected Quantity: {order_quantity}, MOQ: {moq}")


                solution_data.append({
                    'Product_Code': product_code,
                    'Name': product_name,
                    'Order Quantity': order_quantity,
                    'Expected Profit': expected_profit,
                    'Scenario': int(scenario),
                    'Probability': probability
                })

            # Print final totals
            print(f"Final Total CBM: {total_cbm}")
            print(f"Final Total Weight: {total_weight}")
            print(f"Final Total Budget: {total_budget}")

            # Create a DataFrame and export to Excel
            solution_df = pd.DataFrame(solution_data)
            solution_df.to_excel('shipment_optimization_solution.xlsx', index=False)

        except CplexError as e:
            print(e)
#Can change the iteration by running this taking every solution, and max profit and remove products until the constraints are met. 


