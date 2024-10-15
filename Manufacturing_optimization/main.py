import pandas as pd
from optimizer import RawMaterialProcurementOptimizer

finished_raw_data = pd.read_excel('finished_raw_ratio_rate.xlsx', engine = 'openpyxl')
sales_data = pd.read_excel('Average_sales_product.xlsx', engine = 'openpyxl')
raw_rate = pd.read_excel('raw_rate.xlsx', engine = 'openpyxl')
    
budget = sales_data['xval'].sum() * 0.8  # Example budget

optimizer = RawMaterialProcurementOptimizer(finished_raw_data, sales_data, raw_rate, budget)
optimizer.display_results()
