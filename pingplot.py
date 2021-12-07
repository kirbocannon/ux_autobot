import matplotlib.pyplot as plt
import numpy as np
import re



def graph_ping_output(filename, reg):
    with open(filename, "rb") as f:
        data = f.read().decode(encoding='UTF16').rstrip()
        ping_results = data.split("\n")
        ping_results = ping_results[:2500]

        ping_datapoints = []
        for ping_result in ping_results:
            try:
                #time_match = ping_result.split("-")[0].strip()
                ms_match = re.match(f".*{reg}=(?P<ms>.*)ms.*", ping_result)
                ping_datapoints.append(int(ms_match.group("ms")))
                #print(time_match, ms_match.group("ms"))
            except:
                continue

        y = np.array(ping_datapoints)
        x = np.array([i for i in range(len(ping_datapoints))])

        p = plt.figure(1)

        # set labels
        plt.title(f"Ping Results")
        plt.xlabel("ping count")
        plt.ylabel("Ping Time (ms)")

        # draw plot
        plt.plot(x, y, label=filename)
            
        # plt.show()
        #plt.savefig(f"{filename}_ping_graph.png")



if __name__ == '__main__':
    graph_ping_output('ping_output_google_dns.txt', "time")
    graph_ping_output('ping_output_sea_cdn.txt', "time")
    graph_ping_output('ping_output-dfw5-1.txt', "tiempo")

    plt.legend()
    plt.show()
    