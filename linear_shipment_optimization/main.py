
from optimizer import ShipmentOptimizer
from visualizer import OptimizationVisualizer, OptimizationPlotter

def main():
    shipment_name = 'shipment_linear'
    optimizer = ShipmentOptimizer(shipment_name+'.xlsx')
    optimizer.load_data()
    
    # Constraints
    budget = 6600000  
    cbm = 33 
    weight = 28000  

    optimizer.set_constraints(budget, cbm, weight)
    optimizer.setup_problem()
    

    result = optimizer.solve_iteratively()
    print("Total Profit:", result['total_profit'])
    for product, quantity in result['product_quantities'].items():
        print(f"Product {product}: {quantity} units")
    
    print(optimizer.objective_values)
    # visualizer = OptimizationVisualizer(optimizer.objective_values)
    # visualizer.run_animation()

    optimizer.save_results_to_excel(result, shipment_name+'_optimized.xlsx')

    plotter = OptimizationPlotter(optimizer.objective_values)
    plotter.plot_progress()

if __name__ == '__main__':
    main()


# next step # add complementary constraints for basket products, ensure to use recent products
