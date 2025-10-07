import matplotlib.pyplot as plt
import sqlite3

NIST_PARAMS = {2: (2,39), 3: (4,49), 5:(2,60)}

def plot(level):
	eta, tau = NIST_PARAMS[level]
	database = 'runs.db'
	conn = sqlite3.connect(database)
	cursor = conn.cursor()
	cursor.execute('select m,p, count(*), sum(s1) as ILP ,sum(s2) as L1,sum(s3) as huber,sum(s4) as cauchy, sum(s5) as L2 from compare where eta = ? and tau = ? group by m,p order by p, m;', (eta, tau))
	data = cursor.fetchall()
	conn.close()
	contaminations = list(set(row[1] for row in data))
	contaminations.sort()

	min_m_ILP = [min((row[0] for row in data if row[3] is not None and row[3]/row[2] >= 0.95 and row[1] == p), default = None) for p in contaminations]
	min_m_L1  = [min((row[0] for row in data if row[4] is not None and row[4]/row[2] >= 0.95 and row[1] == p), default = None) for p in contaminations]
	min_m_hub = [min((row[0] for row in data if row[5] is not None and row[5]/row[2] >= 0.95 and row[1] == p), default = None) for p in contaminations]
	min_m_cau = [min((row[0] for row in data if row[6] is not None and row[6]/row[2] >= 0.95 and row[1] == p), default = None) for p in contaminations]
	min_m_L2  = [min((row[0] for row in data if row[7] is not None and row[7]/row[2] >= 0.95 and row[1] == p), default = None) for p in contaminations]
	plt.figure(figsize=(5.5, 4))
	plt.yscale('log', base = 2)
	plt.xticks([x/10 for x in range(10)])
	plt.plot(contaminations, min_m_ILP, 'o-', label = 'ILP')
	plt.plot(contaminations, min_m_L1 , 'd-', label = 'L1')
	plt.plot(contaminations, min_m_hub, 'v-', label = 'Huber')
	plt.plot(contaminations, min_m_cau, 's-', label = 'Cauchy')
	plt.plot(contaminations, min_m_L2 , '^-', label = 'L2')
	plt.xlabel('concealment rate')
	plt.ylabel('no. of measurements')
	plt.legend()
	plt.title(f'Measurements for NIST Level {level}')
	plt.savefig(f'data/NIST{level}.pdf')
	plt.close()
