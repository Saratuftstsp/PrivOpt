import os
import argparse



def main():
    parser = argparse.ArgumentParser(description='Clean plans to paste into pg_visualizer.')
    #parser.add_argument('sys_cat_config', type=str, help='How the System Catalog was modified to get these plans.')
    parser.add_argument('plan_file_dir', type=str, help="Directory of plan file.")
    parser.add_argument('plan_file_name', type=str, help="Name of plan file.")
    args = parser.parse_args()
    f1 = open(args.plan_file_dir+args.plan_file_name+".txt", "r")
    s=""
    for line in f1:
        s+= line.strip()[2:-3] + "\n"

    f1.close()
        
    f2 = open(args.plan_file_dir+args.plan_file_name+"_clean.txt", "w")
    f2.write(s)
    f2.close()
        
            
        
if __name__ == '__main__':
    main()