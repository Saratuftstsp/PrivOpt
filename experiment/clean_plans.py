import os
def main():
    dir = "/Users/saraalam/Desktop/PrivOptCode/experiment/exec_plans/"
    dir2 = "/Users/saraalam/Desktop/PrivOptCode/experiment/exec_plans2/"
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