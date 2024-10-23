import matplotlib.pyplot as plt
import numpy as np
import os
import argparse


def plot(qnum, data, save_dir):

    # Define the data
    x = []
    y = []
    for key in data:
        x.append(key)
    x.sort()
    for xval in x:
        y.append(data[xval])
        
    xarr = np.array(x)
    yarr = np.array(y)

    # Create the plot
    plt.figure(figsize=(10, 5))
    plt.plot(xarr, yarr, label='y = runtime', color='blue')
    plt.title('Plot of runtime vs epsilon for query'+str(qnum))
    plt.xlabel('x')
    plt.ylabel('y')
    plt.legend()
    plt.grid()

    # Specify the directory to save the plot
    save_directory = 'your/directory/path'  # Replace with your desired directory
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)  # Create the directory if it doesn't exist

    # Save the plot
    plot_filename = os.path.join(save_dir, 'plot_runtime_vs_epsilon_for_q'+str(qnum)+'.png')
    plt.savefig(plot_filename)

    # Show the plot (optional)
    #plt.show()

    print(f'Plot saved to {plot_filename}')
    
def get_data(dirname):
    data_dict ={}
    for fname in os.listdir(dirname):
        if ".txt" in fname:
            fname_split = fname.split("_")
            if len(fname_split)==4:
                eps = float(fname_split[3][0:-4])
                f1 = open(dirname+fname, "r")
                for line in f1:
                    t = float(line.strip().split(" ")[1])
                    if eps not in data_dict:
                        data_dict[eps] = []
                    data_dict[eps].append(t)
                f1.close()
    return data_dict
    
def data_per_q(data):
    dpq = {}
    for i in range(1, 6):
        dpq[i] = {}
    
    for key in data:
        for i in range(1, 6):
            dpq[i][key]=data[key][i-1]
            
    '''for i in range(1,6):
        print(dpq[i])'''
        
    return dpq
            
    
def main():
    parser = argparse.ArgumentParser(description='Plot runtime vs epsilon.')
    parser.add_argument('data_directory', type=str, help='Directory with files containing data')
    parser.add_argument('plots_directory', type=str, help='Directory to save the plot')
    
    args = parser.parse_args()
    
            
    data = get_data(args.data_directory)
    dpq = data_per_q(data)
    
    for qnum in dpq:
        plot(qnum, dpq[qnum], args.plots_directory)
    

if __name__ == '__main__':
    main()

# example data_dir
# /Users/saraalam/Desktop/PrivOptCode/experiment/Old_exps/exp1/

# example plots dir
# /Users/saraalam/Desktop/PrivOptCode/experiment/Old_exps/exp1/plots/