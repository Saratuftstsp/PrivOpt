import matplotlib.pyplot as plt
import numpy as np
import argparse
import os

def get_data(fname):
    f = open(fname, "r")
    data_dict ={}
    for line in f:
        line_lst = line.strip().split(" ")
        data_dict[line_lst[0]] = float(line_lst[1])
    f.close()
    return data_dict

def plot_bars(array1, array2, array3, labels, plotname):

    # Number of labels
    x = np.arange(len(labels))

    # Width of a single bar
    width = 0.25

    # Create the plot
    fig, ax = plt.subplots()

    # Plot each array, offsetting the x position
    ax.bar(x - width, array1, width, label='Oblivious', color='#26428B')
    ax.bar(x,         array2, width, label='DP', color='#6495ED')
    ax.bar(x + width, array3, width, label='Public', color='#ABCDEF')

    # Add labels, title and legend
    ax.set_xlabel("Queries")
    ax.set_ylabel("Runtimes as ratio of Public Runtimes")
    ax.set_title("Runtime Ratio Bar Chart")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()

    # Save the plot to a file
    plt.savefig("rt_bars_" + plotname + ".jpg", dpi=500)


    plt.tight_layout()
    #plt.show()
    
def plot_aggregates(rtimes_obl, rtimes_pub, rtimes_noisy, case):
    dpf_sr, ndpf_sr, all_sr = [0, 0, 0], [0, 0, 0], [0, 0, 0] # idx 0 of each list is obl, idx 1 of each lst is noisy and idx 2 is public
    labels = ["DP-friendly", "Not DP-friendly", "Full Workload"]
    queries_included_dict = {}
    for label in labels:
        queries_included_dict[label] = []
    for query in rtimes_obl:
        if (query in rtimes_pub) and (query in rtimes_noisy) and (query not in ["7a","28a","29a"]):#["2a","3a","4a","5a","7a","9a","13a","23a", "27a", "28a","29a"]):
            obl_rt = rtimes_obl[query]
            noisy_rt = rtimes_noisy[query]
            pub_rt = rtimes_pub[query]
            if noisy_rt < obl_rt: # DP runtime is better than oblivious runtime
                dpf_sr[0] += obl_rt
                dpf_sr[1] += noisy_rt
                dpf_sr[2] += pub_rt
                queries_included_dict["DP-friendly"].append(query)
            else:
                ndpf_sr[0] += obl_rt
                ndpf_sr[1] += noisy_rt
                ndpf_sr[2] += pub_rt
                queries_included_dict["Not DP-friendly"].append(query)
            all_sr[0] += obl_rt
            all_sr[1] += noisy_rt
            all_sr[2] += pub_rt
    
    if dpf_sr[0] > 0:
        dpf_sr = [dpf_sr[i]/dpf_sr[2] for i in range(3)]
    ndpf_sr = [ndpf_sr[i]/ndpf_sr[2] for i in range(3)]
    all_sr = [all_sr[i]/all_sr[2] for i in range(3)]
    
    print(queries_included_dict["DP-friendly"])
    print(dpf_sr)
    print(queries_included_dict["Not DP-friendly"])
    print(ndpf_sr)
    print(all_sr)
    
    s1 = [1,2,3]
    s2 = [4,5,6]
    s3 = [7,8,9]

    #plot_bars(s1, s2, s3, labels, case+"_test")
    plot_bars([dpf_sr[0], ndpf_sr[0], all_sr[0]], [dpf_sr[1], ndpf_sr[1], all_sr[1]], [dpf_sr[2], ndpf_sr[2], all_sr[2]], labels, case+"_sum_ratios")
    #plot_bars([dpf_sr[0], ndpf_sr[0], all_sr[0]], [dpf_sr[1], ndpf_sr[1], all_sr[1]], [dpf_sr[2], ndpf_sr[2], all_sr[2]], labels, case+"_sum_ratios_7_28_29")
    
    
def main():
    
    parser = argparse.ArgumentParser(description='Plot runtimes for oblivous/noisy/public scenarios.')
    parser.add_argument('case', type=str, help='Name of the scenario it is, eg: oblivious_w_noisy_nullfrac')
    
    args = parser.parse_args()
    
    rtimes_pub = get_data("rtimes_public.txt")
    rtimes_obl = get_data("rtimes_oblivious.txt")
    rtimes_noisy = {} #get_data("rtimes_"+args.case+".txt")
    #est_costs = get_data("bsl1_est_costs.txt") 
    
    dir = "/Users/saraalam/Desktop/curr_work/obl_wn_nullfrac_runs"
    run_dict = {}
    for fname in os.listdir(dir):
        rtimes = get_data(dir+"/"+fname)
        for query in rtimes:
            rt = rtimes[query]
            if query not in run_dict:
                run_dict[query] = []
            run_dict[query].append(rt)
    for query in run_dict:
        rtlst = run_dict[query]
        rtimes_noisy[query] = float(sum(rtlst))/len(rtlst)
    

    y1, y2, y3 = [], [], []
    labels = []
    for query in rtimes_obl:
        if (query in rtimes_pub) and (query in rtimes_noisy) and query not in ["4a","5a","23a"]:
            pub_runtime = rtimes_pub[query]
            dp_runtime = rtimes_noisy[query]
            oblivious_runtime = rtimes_obl[query]
            y1.append(oblivious_runtime/pub_runtime)
            y2.append(dp_runtime/pub_runtime)
            y3.append(1)
            labels.append(query)
        

    plot_bars(y1[0:11],y2[0:11],y3[0:11],labels[0:11], args.case+"_1_11")
    plot_bars(y1[11:20],y2[11:20],y3[11:20],labels[11:20], args.case+"_11_20")
    plot_aggregates(rtimes_obl, rtimes_pub, rtimes_noisy, args.case)
    
if __name__=='__main__':
    main()
