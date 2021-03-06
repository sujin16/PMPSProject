from pykrige.ok import OrdinaryKriging
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import cm
from mpl_toolkits.mplot3d import axes3d
from scipy.interpolate import griddata as gd

import pybrain.datasets as pd
from pybrain.tools.shortcuts import buildNetwork
from pybrain.supervised.trainers import BackpropTrainer
from module.valueZ import read_temp
import datetime as dt

total ={}
grid_array =[]

start_time =''
end_time= ''

class Plot:
    def __init__(self, front_num, end_num, theme, min_bound, max_bound, interval, p_value, extr_interval, model, method):
        super().__init__()

        self.front_num = front_num
        self.end_num = end_num
        self.theme = theme
        self.interval = interval
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.p_value = p_value
        self.extr_interval = extr_interval
        self.method = method
        self.interpol_method = 'cubic'
        self.model = model

        self.x = []
        self.y = []

        for i in range(front_num):
            for j in range(end_num):
                self.x.append(i + 1)
                self.y.append(j + 1)

        z = np.random.uniform(low=0, high=40, size=(front_num * end_num,))
        self.sample_data = np.c_[self.x, self.y, z]

    def main(self):
        if (self.model == 'Neural'):
            self.plot(method=self.method, title='Neural net')

        if (self.model == 'Kriging'):
            self.plot(method=self.method, title='Kriging')

        if (self.model == 'Nearest'):
            self.plot(method=self.method, title='Nearest')


    def neural_net(self,extrapolation_spots, data):
        net = buildNetwork(2, 10, 1)
        ds = pd.SupervisedDataSet(2, 1)

        for row in self.sample_data:
            ds.addSample((row[0], row[1]), (row[2],))
        trainer = BackpropTrainer(net, ds)
        trainer.trainUntilConvergence()

        new_points = np.zeros((len(extrapolation_spots), 3))
        new_points[:, 0] = extrapolation_spots[:, 0]
        new_points[:, 1] = extrapolation_spots[:, 1]
        for i in range(len(extrapolation_spots)):
            new_points[i, 2] = net.activate(extrapolation_spots[i, :2])
        combined = np.concatenate((data, new_points))
        return combined

    def nearest_neighbor_interpolation(self,data, x, y, p=0.5):
        n = len(data)
        vals = np.zeros((n, 2), dtype=np.float64)
        distance = lambda x1, x2, y1, y2: (x2 - x1) ** 2 + (y2 - y1) ** 2
        for i in range(n):
            dis = distance(data[i, 0], x, data[i, 1], y)
            if(dis !=0):
                vals[i, 0] = data[i, 2] / (dis) ** p
                vals[i, 1] = 1 / (dis) ** p
            else:
                break

        if(np.sum(vals[:, 1]) !=0):
            z = np.sum(vals[:, 0]) / np.sum(vals[:, 1])
            return z
        else:
            return None


    def get_plane(self, xl, xu, yl, yu, i):
        xx = np.arange(xl, xu, i)
        yy = np.arange(yl, yu, i)
        extrapolation_spots = np.zeros((len(xx) * len(yy), 2))
        count = 0
        for i in xx:
            for j in yy:
                extrapolation_spots[count, 0] = i
                extrapolation_spots[count, 1] = j
                count += 1
        return extrapolation_spots

    def kriging(self,data, extrapolation_spots):
        gridx = np.arange(1.0, self.front_num, self.end_num)
        gridy = np.arange(1.0, self.front_num, self.end_num)
        OK = OrdinaryKriging(data[:, 0], data[:, 1], data[:, 2], variogram_model='spherical',verbose=False, nlags=100)

        z, ss = OK.execute('grid', gridx, gridy)
        return gridx, gridy, z, ss

    def extrapolation(self,data, extrapolation_spots, model='Nearest'):
        if model == 'Kriging':
            xx, yy, zz, ss = self.kriging(data, extrapolation_spots)

            new_points = np.zeros((len(yy) * len(zz), 3))
            count = 0
            for i in range(len(xx)):
                for j in range(len(yy)):
                    new_points[count, 0] = xx[i]
                    new_points[count, 1] = yy[j]
                    new_points[count, 2] = zz[i, j]
                    count += 1
            combined = np.concatenate((data, new_points))
            return combined

        if model == 'Nearest':
            new_points = np.zeros((len(extrapolation_spots), 3))
            new_points[:, 0] = extrapolation_spots[:, 0]
            new_points[:, 1] = extrapolation_spots[:, 1]
            for i in range(len(extrapolation_spots)):
                new_points[i, 2] = self.nearest_neighbor_interpolation(data,extrapolation_spots[i, 0],extrapolation_spots[i, 1], self.p_value)
                combined = np.concatenate((data, new_points))
            return combined

    def interpolation(self,data):
        gridx, gridy = np.mgrid[1:self.front_num:50j, 1:self.end_num:50j]
        gridz = gd(data[:, :2], data[:, 2], (gridx, gridy), method=self.interpol_method)
        return gridx, gridy, gridz



    def plot(self,method='gradation', title='Nearest'):

        extrapolation_spots = self.get_plane(1, self.front_num, 1, self.end_num, self.extr_interval)

        def update(i):
            now = dt.datetime.now().strftime('%H:%M:%S')
            update_z = read_temp(self.front_num) # read_temp 바꾸기
            global start_time, end_time, grid_array,total

            if (update_z.size == 0):
                fig.suptitle('finish', fontsize=18)
                end_time = now
                ani._stop()

                print(start_time)
                print(end_time)
                plt.close('all')
                return now

            if (update_z.all()):

                if (len(total) == 0):
                    start_time = now

                total[now] = update_z
                update_data = np.c_[self.x, self.y, update_z]

                if (title == 'Nearest'):
                    update_extra = self.extrapolation(update_data, extrapolation_spots, model='Nearest')
                if (title == 'Kriging'):
                    update_extra = self.extrapolation(update_data, extrapolation_spots, model='Kriging')
                if (title == 'Neural net'):
                    update_extra = self.neural_net(extrapolation_spots, update_data)

                gridx_update, gridy_update, gridz_update = self.interpolation(update_extra)

                grid_array =[]

                grid_array.append(gridx_update) #0. 보간법이 적용된 x 값
                grid_array.append(gridy_update) #1. 보간법이 적용된 y 값
                grid_array.append(gridz_update) #2. 보간법이 적용된 z 값
                grid_array.append(update_z)     #3. 실제 센서 값

                ax.clear()

                if(method =='gradation'):
                    ax.plot_surface(gridx_update, gridy_update, gridz_update, alpha=0.5, cmap=self.theme)
                    ax.set_zbound(self.min_bound, self.max_bound)
                    ax.view_init(azim=45)

                if (method == 'wireframe'):
                    ax.plot_wireframe(gridx_update, gridy_update, gridz_update, alpha=0.5)
                    ax.scatter(update_data[:, 0], update_data[:, 1], update_data[:, 2], c='red')
                    ax.set_zbound(self.min_bound, self.max_bound)
                    ax.view_init(azim=45)

                if (method == 'contour'):
                    ax.contourf(gridx_update, gridy_update, gridz_update, zdir='z', offset=self.min_bound, cmap=self.theme)
                    ax.contourf(gridx_update, gridy_update, gridz_update, zdir='x', offset=1, cmap=self.theme)
                    ax.contourf(gridx_update, gridy_update, gridz_update, zdir='y', offset=1, cmap=self.theme)
                    ax.set_zbound(self.min_bound, self.max_bound)
                    ax.view_init(azim=45)

                return ax,


        fig = plt.figure(figsize=(10, 10))
        fig.suptitle(title, fontsize=18)
        ax = fig.gca(projection='3d')
        ani = animation.FuncAnimation(fig, update, interval=self.interval)
        plt.show()



def Main(front_num,end_num, theme, min_bound, max_bound,interval, p_value, extr_interval, model,method):
    #1. plot 만들기
    plot = Plot(front_num, end_num, theme, min_bound, max_bound,interval, p_value, extr_interval, model, method)
    # 2. plot main 함수 실행
    plot.main()
    #sys.exit()

    return grid_array


# result = Main(
#      front_num = 10,
#      end_num = 10,
#      theme="coolwarm",
#      min_bound=0,
#      max_bound=110,
#      interval=1000,
#      p_value=0.5,
#      extr_interval=30,
#      model='Nearest',  # 'Nearest', 'Kriging', 'Neural'
#      method='gradation'# gradation contour rotate wireframe
#      )
# print('---------  end result  ------------')


