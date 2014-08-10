'''
Created on Aug 9, 2014

@author: jeromethai
'''

import numpy as np
import numpy.random as ra
from util import sample_line, sample_box, create_networkx_graph
import networkx as nx    
import matplotlib.pyplot as plt


class Waypoints:
    """Waypoints containing geometry, N waypoints, and a shape"""
    def __init__(self, geo, shape='Shape'):
        self.geometry = geo
        self.shape = shape
        self.N = 0
        self.wp = {}
        
        
    def closest_to_point(self, point):
        """Find closest waypoint to a point (x,y)"""
        min = np.inf
        for id,p in self.wp.items():
            d = np.linalg.norm([point[0]-p[0], point[1]-p[1]])
            if d < min: min, wp_id = d, id
        return wp_id
        
        
    def closest_to_line(self, directed_line, n):
        """Find list of closest waypoints to a directed_line
        
        Parameters:
        ----------
        directed_line: (x1,y1,x2,y2)
        n: number of points to take on the line
        """    
        x1,y1,x2,y2 = directed_line
        for k,t in enumerate(np.linspace(0,1,n)):
            if k == 0: ids = [self.closest_to_point((x1,y1))]
            if k > 0:
                id = self.closest_to_point((x1+t*(x2-x1), y1+t*(y2-y1)))
                if id != ids[-1]: ids.append(id)
        return ids


    def closest_to_polyline(self, polyline, n):
        """Find list of closest waypoints to a directed polyline
        
        Parameters:
        ----------
        polyline: list of directed lines [(x1,y1,x2,y2)]
        n: number of points to take on each line of the polyline
        """
        ids = []
        for k, line in enumerate(polyline):
            if k == 0: ids = self.closest_to_line(line, n)
            if k > 0:
                tmp = self.closest_to_line(line, n)
                if ids[-1] == tmp[0]: ids += tmp[1:]
                if ids[-1] != tmp[0]: ids += tmp
        return ids
    
    
    def closest_to_path(self, graph, path_id, n):
        """Find list of closest waypoints to a path in the graph
        
        Parameters:
        ----------
        graph: Graph object
        path_id: path id of a path in the graph
        n: number of points to take on each link of the path
        """
        polyline = []
        for link in graph.paths[path_id].links:
            x1, y1 = graph.nodes_position[link.startnode]
            x2, y2 = graph.nodes_position[link.endnode]
            polyline.append((x1,y1,x2,y2))
        return self.closest_to_polyline(polyline, n)
    
    
    def draw_waypoints(self, graph=None, wps=None, ps=None, path_id=None):
        """Draw waypoints and graph.
        Can specify specific waypoints, points, and path to draw
        
        Parameters:
        ----------
        graph: Graph object
        wps: list [(color, list of waypoint_ids)] following matlab colorspec
        ps: list [(color, list of points)] following matlab colorspec
        path_id: path to draw
        """
        if graph is not None:
            G, pos = create_networkx_graph(graph), graph.nodes_position
            nx.draw_networkx_edges(G, pos, arrows=False)
            if path_id is not None:
                edges = [(link.startnode, link.endnode) for link in graph.paths[path_id].links]
                nx.draw_networkx_edges(G, pos, edgelist=edges, width=7, alpha=0.5, edge_color='r', arrows=False)
        if self.shape == 'Bounding box':
            if self.N0 > 0:
                xs = [self.wp[i+1][0] for i in range(self.N0)]
                ys = [self.wp[i+1][1] for i in range(self.N0)]
                plt.plot(xs, ys, 'co', label='uniform')
            if len(self.lines) > 0:
                xs = [p[0] for line in self.lines.values() for p in line.wp.values()]
                ys = [p[1] for line in self.lines.values() for p in line.wp.values()]
                plt.plot(xs, ys, 'mo', label='lines')
            if len(self.regions) > 0:
                xs = [p[0] for r in self.regions.values() for p in r.wp.values()]
                ys = [p[1] for r in self.regions.values() for p in r.wp.values()]
                plt.plot(xs, ys, 'go', label='regions')
        else:
            if self.N > 0:
                xs = [self.wp[i+1][0] for i in range(self.N)]
                ys = [self.wp[i+1][1] for i in range(self.N)]
                plt.plot(xs, ys, 'co', label='uniform')
        if wps is not None:
            for color, ids, label in wps:
                xs, ys = [self.wp[id][0] for id in ids], [self.wp[id][1] for id in ids]
                plt.plot(xs, ys, color+'o', label=label)
        if ps is not None:
            for color, ps, label in ps:
                xs, ys = [p[0] for p in ps], [p[1] for p in ps]
                plt.plot(xs, ys, color+'o', label=label)      
        plt.legend()
        plt.show()
 

    def generate_wp_flows(self, graph, n, tol=1e-3):
        """Generate Waypoint flows
        
        Parameters:
        ----------
        graph: Graph object with path flows in it
        n: number of points to take on each link of paths
        """
        wp_flow = {}
        for path_id, path in graph.paths.items():
            if path.flow > tol:
                ids = self.closest_to_path(graph, path_id, n)
                wp_flow[path_id] = (ids, path.flow)
        return wp_flow
     
       
class Rectangle(Waypoints):
    """Rectangle containing geo=(x1,y1,x2,y2), N waypoints, and a shape"""
    def __init__(self, geo):
        Waypoints.__init__(self, geo, 'Rectangle')
        
    def populate(self, N, first=1):
        """Uniformly sample N points in rectangle
        with first the first key used in wp"""
        self.N = N
        ps = sample_box(N, self.geometry)
        self.wp = {id: p for id,p in enumerate(ps,first)}
        if self.shape == 'Bounding box': self.N0 = self.N


class BoundingBox(Rectangle):
    """BoundingBox containing geo=(x1,y1,x2,y2), N waypoints, shape, lines, regions
    The bounding box have a dictionary of all waypoints in the area including the
    ones associated to lines and regions"""
    def __init__(self, geo):
        Rectangle.__init__(self, geo)
        self.shape = 'Bounding box'
        self.lines = {}
        self.num_lines = 0
        self.regions = {}
        self.num_regions = 0
        self.N0 = 0 # number of uniform samples in the whole region
        
    def add_rectangle(self, geo, N):
        """Add a rectangular region with N points"""
        r = Rectangle(geo)
        r.populate(N, self.N+1)
        self.num_regions += 1
        self.regions[self.num_regions] = r
        self.N += N
        self.wp = dict(self.wp.items() + r.wp.items())
        
    def add_line(self, geo, N, scale):
        """Add a line with N points"""
        l = Line(geo)
        l.populate(N, self.N+1, scale)
        self.num_lines += 1
        self.lines[self.num_lines] = l
        self.N += N
        self.wp = dict(self.wp.items() + l.wp.items())
                    
        
class Line(Waypoints):
    """Class Line containing geo=(x1,y1,x2,y2) waypoints"""
    def __init__(self, geo):
        Waypoints.__init__(self, geo, 'Line')
        
    def populate(self, N, first=1, scale=1e-8):
        """Sample N points along line
        with first the first key used in wp"""
        self.N = N
        ps = sample_line(N, self.geometry, scale)
        self.wp = {id: p for id,p in enumerate(ps,first)}


def sample_waypoints(graph, N0, N1, regions, margin):
    """Sample waypoints on graph
    
    Parameters:
    -----------
    graph: Graph object
    N0: number of background samples
    N1: number of samples on links
    regions: list of regions, regions[k] = (geometry, N_region)
    margin: % size of margin around the graph
    """
    xs = [p[0] for p in graph.nodes_position.values()]
    ys = [p[1] for p in graph.nodes_position.values()]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    w, h = max_x-min_x, max_y-min_y
    x1, x2, y1, y2 = min_x - w*margin, max_x + w*margin, min_y - h*margin, max_y + h*margin
    WP = BoundingBox((x1, y1, x2, y2))
    WP.populate(N0)
    total_length, lines = 0, []
    for link in graph.links.values():
        xs, ys = graph.nodes_position[link.startnode]
        xt, yt = graph.nodes_position[link.endnode]
        length = np.linalg.norm([xs-xt, ys-yt])
        total_length += length
        lines.append([(xs,ys,xt,yt), length])
    weights = [line[1]/total_length for line in lines]
    Ns = ra.multinomial(N1, weights, size=1)[0]
    for k,line in enumerate(lines): WP.add_line(line[0], Ns[k], 0.1)
    for r in regions: WP.add_rectangle(r[0], r[1])
    return WP
    

if __name__ == '__main__':
    pass