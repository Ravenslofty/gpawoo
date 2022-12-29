from amaranth import *

# a rough guide to triangle setup:
#
# take a triangle ABC formed of lines AB, BC, and CA:
#
#      A
#     / \
#    /   \
#   /     \
#  B-------C
#
# the algorithm used in this code was described by Juan Pineda in
#  "A Parallel Algorithm for Polygon Rasterisation", June 1988.
#
# Pineda's rasteriser defines an edge function between a line AB and a point P:
#
# edge(A, B, P) = (P.x - A.x)(B.y - A.y) - (P.y - A.y)(B.x - A.x)
#
# this function returns a value with a sign based on where P is relative to AB:
#
#     B
# ---/+
# --/++
# -/+++
# A
#
# (if P is exactly on line AB, the value is zero.)
#
# if one calculates this edge function for all three lines of a triangle, then
# a point is inside that triangle if the signs of all three functions agree.
# however, what that sign is depends on the "winding" of the triangle:
#
#    B
#   / \
#  /   \
# A-----C   ABC has clockwise winding, sign inside triangle is positive
#
#
#    C
#   / \
#  /   \
# A-----B   ABC has counterclockwise winding, sign inside triangle is negative
#
# triangle winding can be flipped by swapping two vertices. as such,
# TriangleRender assumes a counter-clockwise winding with negativeve internal
# sign to simplify implementation and allow for back-face culling. 
# counter-clockwise winding is the default for both DirectX and OpenGL.
#
# with the algorithm explanation out of the way, the necessary setup math:
# (all coordinates are in Q12.4 fixed-point format unless otherwise specified.)
#
# i_xy_a: (A.y << 16) | A.x
# i_xy_b: (B.y << 16) | B.x
# i_xy_c: (C.y << 16) | C.x
#
# i_start_x: min(A.x, B.x, C.x)
# i_start_y: min(A.y, B.y, C.y)
# i_stop_x:  max(A.x, B.x, C.x)
# i_stop_y:  max(A.y, B.y, C.y)
#
# let P be the point of (i_start_x, i_start_y) for setup calculation:
#
# i_edge_ab: edge(A, B, P)
# i_edge_bc: edge(B, C, P)
# i_edge_ca: edge(C, A, P)
#
# i_edge_ab_dx: B.y - A.y
# i_edge_ab_dy: A.x - B.x
# i_edge_bc_dx: C.y - B.y
# i_edge_bc_dy: B.x - C.x
# i_edge_ca_dx: A.y - C.y
# i_edge_ca_dy: C.x - A.x


class TriangleRender(Elaboratable):
    def __init__(self):
        self.i_xy_a  = Signal(32)
        self.i_xy_b  = Signal(32)
        self.i_xy_c  = Signal(32)

        self.i_start_x = Signal(16)
        self.i_start_y = Signal(16)
        self.i_stop_x  = Signal(16)
        self.i_stop_y  = Signal(16)

        self.i_edge_ab = Signal(signed(32))
        self.i_edge_bc = Signal(signed(32))
        self.i_edge_ca = Signal(signed(32))

        self.i_edge_ab_dx = Signal(signed(16))
        self.i_edge_ab_dy = Signal(signed(16))
        self.i_edge_bc_dx = Signal(signed(16))
        self.i_edge_bc_dy = Signal(signed(16))
        self.i_edge_ca_dx = Signal(signed(16))
        self.i_edge_ca_dy = Signal(signed(16))

        self.o_xy    = Signal(32)
        self.o_valid = Signal()
        self.o_done  = Signal()

    def elaborate(self, platform):
        m = Module()

        # 12.4 fixed-point
        a_x, a_y = self.i_xy_a[:16], self.i_xy_a[16:]
        b_x, b_y = self.i_xy_b[:16], self.i_xy_b[16:]
        c_x, c_y = self.i_xy_c[:16], self.i_xy_c[16:]
        x        = Signal(16)
        y        = Signal(16)
        x_inc    = Signal(signed(16), reset=(1 << 4))

        valid    = (
            ((self.i_edge_ab < 0) | ((self.i_edge_ab == 0) & ((self.i_edge_ab_dx > 0) | (self.i_edge_ab_dx == 0) & (self.i_edge_ab_dy < 0)))) &
            ((self.i_edge_bc < 0) | ((self.i_edge_bc == 0) & ((self.i_edge_bc_dx > 0) | (self.i_edge_bc_dx == 0) & (self.i_edge_bc_dy < 0)))) &
            ((self.i_edge_ca < 0) | ((self.i_edge_ca == 0) & ((self.i_edge_ca_dx > 0) | (self.i_edge_ca_dx == 0) & (self.i_edge_ca_dy < 0))))
        )

        m.d.sync += [
            self.o_xy.eq(Cat(x, y)),
            self.o_valid.eq(valid),
        ]

        with m.FSM():
            with m.State("WAIT1"):
                m.next = "WAIT2"
            with m.State("WAIT2"):
                m.d.sync += [
                    x.eq(self.i_start_x + (1 << 3)),
                    y.eq(self.i_start_y + (1 << 3)),
                ]
                m.next = "SETUP"
                
            with m.State("SETUP"):
                m.next = "ITERATE"

            with m.State("ITERATE"):
                m.d.sync += [
                    self.i_edge_ab.eq(self.i_edge_ab + self.i_edge_ab_dx),
                    self.i_edge_bc.eq(self.i_edge_bc + self.i_edge_bc_dx),
                    self.i_edge_ca.eq(self.i_edge_ca + self.i_edge_ca_dx),
                    x.eq(x + x_inc),
                ]
                with m.If(((x_inc > 0) & ((x + x_inc) > self.i_stop_x)) | ((x_inc < 0) & ((x + x_inc) <= self.i_start_x))):
                    m.d.sync += [
                        self.i_edge_ab.eq(self.i_edge_ab + self.i_edge_ab_dy + self.i_edge_ab_dx),
                        self.i_edge_bc.eq(self.i_edge_bc + self.i_edge_bc_dy + self.i_edge_bc_dx),
                        self.i_edge_ca.eq(self.i_edge_ca + self.i_edge_ca_dy + self.i_edge_ca_dx),
                        self.i_edge_ab_dx.eq(-self.i_edge_ab_dx),
                        self.i_edge_bc_dx.eq(-self.i_edge_bc_dx),
                        self.i_edge_ca_dx.eq(-self.i_edge_ca_dx),
                        x_inc.eq(-x_inc),
                        y.eq(y + (1 << 4)),
                    ]
                    with m.If((y + (1 << 4)) > self.i_stop_y):
                        m.next = "DONE"

            with m.State("DONE"):
                m.d.sync += self.o_done.eq(1)

        return m


if __name__ == "__main__":
    tr = TriangleRender()
    ports = [
        tr.i_xy_a, tr.i_xy_b, tr.i_xy_c,
        tr.i_start_x, tr.i_start_y, tr.i_stop_x, tr.i_stop_y,
        tr.i_edge_ab, tr.i_edge_bc, tr.i_edge_ca,
        tr.i_edge_ab_dx, tr.i_edge_ab_dy,
        tr.i_edge_bc_dx, tr.i_edge_bc_dy,
        tr.i_edge_ca_dx, tr.i_edge_ca_dy,
        tr.o_xy, tr.o_valid, tr.o_done
    ]

    from amaranth.back import rtlil

    with open("gpu.il", "w") as f:
        f.write(rtlil.convert(tr, ports=ports))

    from amaranth.sim import *

    def test():
        def edge(ax, ay, bx, by, cx, cy): # ax, ay, bx, by, cx, cy all Q12.4
            return (((cx - ax) * (by - ay)) - ((cy - ay) * (bx - ax))) >> 4 # Q24.4 

        a_x, a_y = 0x0949, 0x0449
        b_x, b_y = 0x1EB6, 0x19B6
        c_x, c_y = 0x0949, 0x19B6

        start_x = min(a_x, b_x, c_x)
        start_y = min(a_y, b_y, c_y)
        stop_x  = max(a_x, b_x, c_x)
        stop_y  = max(a_y, b_y, c_y)

        yield tr.i_xy_b.eq(Cat(C(b_x, 16), C(b_y, 16)))
        yield tr.i_xy_a.eq(Cat(C(a_x, 16), C(a_y, 16)))
        yield tr.i_xy_c.eq(Cat(C(c_x, 16), C(c_y, 16)))

        yield tr.i_start_x.eq(start_x)
        yield tr.i_start_y.eq(start_y)
        yield tr.i_stop_x.eq(stop_x)
        yield tr.i_stop_y.eq(stop_y)

        yield tr.i_edge_ab.eq(edge(a_x, a_y, b_x, b_y, start_x, start_y))
        yield tr.i_edge_bc.eq(edge(b_x, b_y, c_x, c_y, start_x, start_y))
        yield tr.i_edge_ca.eq(edge(c_x, c_y, a_x, a_y, start_x, start_y))
        
        yield tr.i_edge_ab_dx.eq(b_y - a_y)
        yield tr.i_edge_ab_dy.eq(a_x - b_x)
        yield tr.i_edge_bc_dx.eq(c_y - b_y)
        yield tr.i_edge_bc_dy.eq(b_x - c_x)
        yield tr.i_edge_ca_dx.eq(a_y - c_y)
        yield tr.i_edge_ca_dy.eq(c_x - a_x)

        yield
        cycles = 1

        while not (yield tr.o_done):
            yield
            cycles += 1
            if (yield tr.o_valid):
                xy = (yield tr.o_xy)
                x = (xy & 0xFFFF) / 16.0
                y = (xy >> 16)    / 16.0
                print((x, y))
        
        print("Took {} cycles".format(cycles))

    sim = Simulator(tr)
    sim.add_clock(1e-9)
    sim.add_sync_process(test)
    with sim.write_vcd("test.vcd", "test.gtkw"):
        sim.run()
