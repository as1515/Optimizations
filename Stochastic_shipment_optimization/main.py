import pandas as pd
from optimizer import StochasticOptimizer

# Load the data
scenario_data = pd.read_excel("scenarios.xlsx", engine = 'openpyxl') 
scenario_data = scenario_data.drop(columns=['Unnamed: 0'])
fixed_data = pd.read_excel("shipment_stochastic.xlsx", engine = 'openpyxl')    
fixed_data = fixed_data.rename(columns = {'Code':'Product_Code'}).drop(columns=['Unnamed: 0'])
merged_data = scenario_data.merge(fixed_data, on='Product_Code', how='left')
merged_data['Demand/month_x'] = merged_data['Demand/month']/merged_data['Pcs/Ctn']
merged_data = merged_data.drop(columns=['Demand/month','Pcs/Ctn']).rename(columns = {'Demand/month_x':'Demand/month'})
merged_data['Profit/unit'] = merged_data['Total_Profit']/merged_data['Demand/month']
merged_data = merged_data.drop(columns=['Total_Profit'])
# merged_data['Product_Code'] = merged_data['Product_Code'].apply(lambda x: f"{x:0>}" if isinstance(x, int) else str(x))
merged_data['Weight/unit'] = merged_data['Weight/unit'].astype(float)
merged_data['MOQ/unit'] = merged_data['MOQ/unit'].astype(float)

merged_data.to_excel('merged_data.xlsx')

budget_limit = 6000000
cbm_limit = 33 
weight_limit = 28000
alpha = 1

optimizer = StochasticOptimizer(merged_data, budget_limit, cbm_limit, weight_limit, alpha)
optimizer.initialize_model()
optimizer.create_decision_variables()
optimizer.add_constraints()
optimizer.solve()
