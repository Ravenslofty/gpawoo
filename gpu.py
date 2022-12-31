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
# TriangleRender assumes a counter-clockwise winding with negative internal
# sign to simplify implementation and allow for back-face culling. 
# counter-clockwise winding is the default for both DirectX and OpenGL.
#
# C-----B   AB is a right edge because B.y > A.y, so is not drawn.
#  \   /    BC is a top edge because B.x < C.x and B.y == C.y, so is drawn.
#   \ /     CA is a left edge because A.y < C.y, so is drawn.
#    A
#
# to avoid multiple pixels being drawn on the edge of two adjacent pixels,
# the Pineda formula is adjusted slightly to make the "top" and "left" edges
# of a triangle count as inside the triangle, but "bottom" and "right" edges
# count as outside the triangle.
#
# with the algorithm explanation out of the way, the necessary setup math:
# (all coordinates are in Q12.4 fixed-point format unless otherwise specified.)
#
# i_xy_a: (A.y << 16) | A.x
# i_xy_b: (B.y << 16) | B.x
# i_xy_c: (C.y << 16) | C.x
#
# i_start_x: min(A.x, B.x, C.x) + 1.0
# i_start_y: min(A.y, B.y, C.y)
# i_stop_x:  max(A.x, B.x, C.x) - 1.0
# i_stop_y:  max(A.y, B.y, C.y)
#
# let P be the point of (i_start_x, i_start_y) for setup calculation:
# let cast(X) be 0.0625 if X is true, and 0.0 if X is false.
#
# i_edge_ab: edge(A, B, P) - cast(A.y < B.y or (A.y == B.y && B.x < A.x))
# i_edge_bc: edge(B, C, P) - cast(B.y < C.y or (B.y == C.y && C.x < B.x))
# i_edge_ca: edge(C, A, P) - cast(C.y < A.y or (C.y == A.y && A.x < C.x))
#
# i_edge_ab_dx: B.y - A.y
# i_edge_ab_dy: A.x - B.x
# i_edge_bc_dx: C.y - B.y
# i_edge_bc_dy: B.x - C.x
# i_edge_ca_dx: A.y - C.y
# i_edge_ca_dy: C.x - A.x
#
# o_xy: ((min(A.y, B.y, C.y) + 0.5) << 16) | (min(A.x, B.x, C.x) + 0.5)
# i_run: 1


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

        self.i_edge_ab_pdx = Signal(signed(16))
        self.i_edge_ab_mdx = Signal(signed(16))
        self.i_edge_ab_dy = Signal(signed(16))
        self.i_edge_bc_pdx = Signal(signed(16))
        self.i_edge_bc_mdx = Signal(signed(16))
        self.i_edge_bc_dy = Signal(signed(16))
        self.i_edge_ca_pdx = Signal(signed(16))
        self.i_edge_ca_mdx = Signal(signed(16))
        self.i_edge_ca_dy = Signal(signed(16))

        self.i_run   = Signal()

        self.o_xy    = Signal(32)
        self.o_valid = Signal()

    def elaborate(self, platform):
        m = Module()

        # 12.4 fixed-point
        a_x, a_y = self.i_xy_a[:16], self.i_xy_a[16:]
        b_x, b_y = self.i_xy_b[:16], self.i_xy_b[16:]
        c_x, c_y = self.i_xy_c[:16], self.i_xy_c[16:]
        x, y     = self.o_xy[:16], self.o_xy[16:]
        x_pinc   = Signal(signed(16), reset=(1 << 4))
        x_minc   = Signal(signed(16), reset=-(1 << 4))

        m.d.sync += self.o_valid.eq((self.i_edge_ab < 0) & (self.i_edge_bc < 0) & (self.i_edge_ca < 0))

        with m.If(self.i_run):
            m.d.sync += [
                self.i_edge_ab.eq(self.i_edge_ab + self.i_edge_ab_pdx),
                self.i_edge_bc.eq(self.i_edge_bc + self.i_edge_bc_pdx),
                self.i_edge_ca.eq(self.i_edge_ca + self.i_edge_ca_pdx),
                x.eq(x + x_pinc),
            ]
            with m.If(((x_pinc > 0) & (x > self.i_stop_x)) | ((x_pinc < 0) & (x <= self.i_start_x))):
                m.d.sync += [
                    self.i_edge_ab.eq(self.i_edge_ab + self.i_edge_ab_dy + self.i_edge_ab_pdx),
                    self.i_edge_bc.eq(self.i_edge_bc + self.i_edge_bc_dy + self.i_edge_bc_pdx),
                    self.i_edge_ca.eq(self.i_edge_ca + self.i_edge_ca_dy + self.i_edge_ca_pdx),
                    Cat(self.i_edge_ab_pdx, self.i_edge_ab_mdx).eq(Cat(self.i_edge_ab_mdx, self.i_edge_ab_pdx)),
                    Cat(self.i_edge_bc_pdx, self.i_edge_bc_mdx).eq(Cat(self.i_edge_bc_mdx, self.i_edge_bc_pdx)),
                    Cat(self.i_edge_ca_pdx, self.i_edge_ca_mdx).eq(Cat(self.i_edge_ca_mdx, self.i_edge_ca_pdx)),
                    Cat(x_pinc, x_minc).eq(Cat(x_minc, x_pinc)),
                    y.eq(y + (1 << 4)),
                    self.i_run.eq((y + (1 << 4)) <= self.i_stop_y),
                ]

        return m


if __name__ == "__main__":
    tr = TriangleRender()
    ports = [
        tr.i_xy_a, tr.i_xy_b, tr.i_xy_c,
        tr.i_start_x, tr.i_start_y, tr.i_stop_x, tr.i_stop_y,
        tr.i_edge_ab, tr.i_edge_bc, tr.i_edge_ca,
        tr.i_edge_ab_pdx, tr.i_edge_ab_mdx, tr.i_edge_ab_dy,
        tr.i_edge_bc_pdx, tr.i_edge_ab_mdx, tr.i_edge_bc_dy,
        tr.i_edge_ca_pdx, tr.i_edge_ca_mdx, tr.i_edge_ca_dy,
        tr.o_xy, tr.o_valid, tr.i_run
    ]

    from amaranth.back import rtlil

    with open("gpu.il", "w") as f:
        f.write(rtlil.convert(tr, ports=ports))

    from amaranth.sim import *

    def test():
        def edge(ax, ay, bx, by, cx, cy): # ax, ay, bx, by, cx, cy all Q12.4
            x = (((cx - ax) * (by - ay)) - ((cy - ay) * (bx - ax))) >> 4 # Q24.4
            x -= int((ax < bx or (ax == bx and by < ay)))
            return x

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

        yield tr.i_start_x.eq(start_x + (1 << 4))
        yield tr.i_start_y.eq(start_y)
        yield tr.i_stop_x.eq(stop_x - (1 << 4))
        yield tr.i_stop_y.eq(stop_y)

        yield tr.i_edge_ab.eq(edge(a_x, a_y, b_x, b_y, start_x, start_y))
        yield tr.i_edge_bc.eq(edge(b_x, b_y, c_x, c_y, start_x, start_y))
        yield tr.i_edge_ca.eq(edge(c_x, c_y, a_x, a_y, start_x, start_y))
        
        yield tr.i_edge_ab_pdx.eq(b_y - a_y)
        yield tr.i_edge_ab_mdx.eq(a_y - b_y)
        yield tr.i_edge_ab_dy.eq(a_x - b_x)
        yield tr.i_edge_bc_pdx.eq(c_y - b_y)
        yield tr.i_edge_bc_mdx.eq(b_y - c_y)
        yield tr.i_edge_bc_dy.eq(b_x - c_x)
        yield tr.i_edge_ca_pdx.eq(a_y - c_y)
        yield tr.i_edge_ca_mdx.eq(c_y - a_y)
        yield tr.i_edge_ca_dy.eq(c_x - a_x)

        yield tr.i_run.eq(1)
        yield tr.o_xy.eq(Cat(C(start_x + (1 << 3), 16), C(start_y + (1 << 3))))

        yield
        cycles = 1

        while (yield tr.i_run):
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
