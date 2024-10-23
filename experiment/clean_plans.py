import os
def main():
    exp_lst = ["nullfrac", "ndist", "mcf"]
    for exp in exp_lst:
        dir = "/Users/saraalam/Desktop/PrivOptCode/experiment/" + exp +"/exec_plans/"
        dir2 = "/Users/saraalam/Desktop/PrivOptCode/experiment/" + exp +"/exec_plans2/"
        
        if not os.path.exists(dir):
            os.makedirs(dir)  # Create the directory if it doesn't exist
            
        if not os.path.exists(dir2):
            os.makedirs(dir2)  # Create the directory if it doesn't existv

        for f in os.listdir(dir):
            f1 = open(dir+f, "r")
            s=""
            for line in f1:
                s+= line.strip()[2:-3] + "\n"

            f1.close()
            
            f2 = open(dir2+f, "w")
            f2.write(s)
            f2.close()
        
            
        
if __name__ == '__main__':
    main()