from amaranth import *


class EdgeFunction(Elaboratable):
    def __init__(self):
        self.i_ax = Signal(16)
        self.i_ay = Signal(16)
        self.i_bx = Signal(16)
        self.i_by = Signal(16)
        self.i_cx = Signal(16)
        self.i_cy = Signal(16)

        self.o    = Signal(signed(32))

    def elaborate(self, _):
        m = Module()

        # Stage 1:
        ca_x = Signal(signed(17))
        ba_y = Signal(signed(17))
        ca_y = Signal(signed(17))
        ba_x = Signal(signed(17))
        a_x = Signal(16)
        a_y = Signal(16)
        b_x = Signal(16)
        b_y = Signal(16)

        m.d.sync += [
            ca_x.eq(self.i_cx - self.i_ax),
            ba_y.eq(self.i_by - self.i_ay),
            ca_y.eq(self.i_cy - self.i_ay),
            ba_x.eq(self.i_bx - self.i_ax),
            a_x.eq(self.i_ax),
            a_y.eq(self.i_ay),
            b_x.eq(self.i_bx),
            b_y.eq(self.i_by),
        ]

        # Stage 2:
        ca_x_ba_y = Signal(signed(34))
        ca_y_ba_x = Signal(signed(34))
        ab_x_le = Signal()
        ab_x_eq = Signal()
        ba_y_le = Signal()

        m.d.sync += [
            ca_x_ba_y.eq(ca_x * ba_y),
            ca_y_ba_x.eq(ca_y * ba_x),
            ab_x_le.eq(a_x < b_x),
            ab_x_eq.eq(a_x == b_x),
            ba_y_le.eq(b_y < a_y),
        ]

        # Stage 3:
        result     = Signal(signed(32))
        adjustment = Signal()

        m.d.sync += [
            result.eq((ca_x_ba_y - ca_y_ba_x) >> 4),
            adjustment.eq(ab_x_le | (ab_x_eq & ba_y_le)),
        ]

        # Stage 4:
        m.d.sync += self.o.eq(result - adjustment)

        return m


class TriangleSetup(Elaboratable):
    def __init__(self):
        self.i_tri_xy_a  = Signal(32)
        self.i_tri_xy_b  = Signal(32)
        self.i_tri_xy_c  = Signal(32)
        self.i_point     = Signal(32)
        self.i_start     = Signal()

        self.o_edge_ab   = Signal(32)
        self.o_edge_bc   = Signal(32)
        self.o_edge_ca   = Signal(32)
        self.o_tri_area  = Signal(32)

        self.o_edge_ab_dx = Signal(16)
        self.o_edge_ab_dy = Signal(16)
        self.o_edge_bc_dx = Signal(16)
        self.o_edge_bc_dy = Signal(16)
        self.o_edge_ca_dx = Signal(16)
        self.o_edge_ca_dy = Signal(16)

        self.o_valid      = Signal()

    def elaborate(self, _):
        m = Module()

        m.submodules.edge_func = edge_func = EdgeFunction()

        a_x, a_y = self.i_tri_xy_a[:16], self.i_tri_xy_a[16:]
        b_x, b_y = self.i_tri_xy_b[:16], self.i_tri_xy_b[16:]
        c_x, c_y = self.i_tri_xy_c[:16], self.i_tri_xy_c[16:]
        p_x, p_y = self.i_point[:16], self.i_point[16:]

        # TODO: can save four subtractions by stealing from the edge function

        m.d.sync += self.o_valid.eq(0)

        with m.FSM():
            with m.State("START"):
                with m.If(self.i_start):
                    m.next = "PUSH_AB"
            with m.State("PUSH_AB"):
                m.d.sync += [
                    edge_func.i_ax.eq(a_x),
                    edge_func.i_ay.eq(a_y),
                    edge_func.i_bx.eq(b_x),
                    edge_func.i_by.eq(b_y),
                    edge_func.i_cx.eq(p_x),
                    edge_func.i_cy.eq(p_y)
                ]
                m.next = "PUSH_BC"
            with m.State("PUSH_BC"):
                m.d.sync += [
                    edge_func.i_ax.eq(b_x),
                    edge_func.i_ay.eq(b_y),
                    edge_func.i_bx.eq(c_x),
                    edge_func.i_by.eq(c_y),
                    edge_func.i_cx.eq(p_x),
                    edge_func.i_cy.eq(p_y)
                ]
                m.next = "PUSH_CA"
            with m.State("PUSH_CA"):
                m.d.sync += [
                    edge_func.i_ax.eq(c_x),
                    edge_func.i_ay.eq(c_y),
                    edge_func.i_bx.eq(a_x),
                    edge_func.i_by.eq(a_y),
                    edge_func.i_cx.eq(p_x),
                    edge_func.i_cy.eq(p_y)
                ]
                m.next = "PUSH_AREA"
            with m.State("PUSH_AREA"):
                m.d.sync += [
                    edge_func.i_ax.eq(a_x),
                    edge_func.i_ay.eq(a_y),
                    edge_func.i_bx.eq(b_x),
                    edge_func.i_by.eq(b_y),
                    edge_func.i_cx.eq(c_x),
                    edge_func.i_cy.eq(c_y)
                ]
                m.next = "POP_AB"
            with m.State("POP_AB"):
                m.d.sync += self.o_edge_ab.eq(edge_func.o)
                m.next = "POP_BC"
            with m.State("POP_BC"):
                m.d.sync += self.o_edge_bc.eq(edge_func.o)
                m.next = "POP_CA"
            with m.State("POP_CA"):
                m.d.sync += self.o_edge_ca.eq(edge_func.o)
                m.next = "POP_AREA"
            with m.State("POP_AREA"):
                m.d.sync += [
                    self.o_tri_area.eq(edge_func.o),

                    self.o_edge_ab_dx.eq(b_y - a_y),
                    self.o_edge_ab_dy.eq(a_x - b_x),
                    self.o_edge_bc_dx.eq(c_y - b_y),
                    self.o_edge_bc_dy.eq(b_x - c_x),
                    self.o_edge_ca_dx.eq(a_y - c_y),
                    self.o_edge_ca_dy.eq(c_x - a_x),

                    self.o_valid.eq(1),
                ]
                m.next = "START"

        return m


class FragmentInTriangleTest(Elaboratable):
    def __init__(self):
        self.i_tri_xy_a   = Signal(32)
        self.i_tri_xy_b   = Signal(32)
        self.i_tri_xy_c   = Signal(32)
        self.i_tri_wz_a   = Signal(32)
        self.i_tri_wz_b   = Signal(32)
        self.i_tri_wz_c   = Signal(32)
        self.i_tri_rgba_a = Signal(32)
        self.i_tri_rgba_b = Signal(32)
        self.i_tri_rgba_c = Signal(32)
        self.i_pnt_xy     = Signal(32)
        self.i_valid      = Signal()

        self.i_edge_ab   = Signal(signed(32))
        self.i_edge_bc   = Signal(signed(32))
        self.i_edge_ca   = Signal(signed(32))
        self.i_tri_area  = Signal(signed(32))

        self.o_tri_xy_a   = Signal(32)
        self.o_tri_xy_b   = Signal(32)
        self.o_tri_xy_c   = Signal(32)
        self.o_tri_wz_a   = Signal(32)
        self.o_tri_wz_b   = Signal(32)
        self.o_tri_wz_c   = Signal(32)
        self.o_tri_rgba_a = Signal(32)
        self.o_tri_rgba_b = Signal(32)
        self.o_tri_rgba_c = Signal(32)
        self.o_pnt_xy     = Signal(32)
        self.o_valid      = Signal()

        self.o_edge_ab   = Signal(signed(32))
        self.o_edge_bc   = Signal(signed(32))
        self.o_edge_ca   = Signal(signed(32))
        self.o_tri_area  = Signal(signed(32))

    def elaborate(self, _):
        m = Module()

        m.d.sync += [
            self.o_valid.eq(self.i_valid & (self.i_edge_ab < 0) & (self.i_edge_bc < 0) & (self.i_edge_ca < 0)),

            self.o_tri_xy_a.eq(self.i_tri_xy_a),
            self.o_tri_xy_b.eq(self.i_tri_xy_b),
            self.o_tri_xy_c.eq(self.i_tri_xy_c),
            self.o_tri_wz_a.eq(self.i_tri_wz_a),
            self.o_tri_wz_b.eq(self.i_tri_wz_b),
            self.o_tri_wz_c.eq(self.i_tri_wz_c),
            self.o_tri_rgba_a.eq(self.i_tri_rgba_a),
            self.o_tri_rgba_b.eq(self.i_tri_rgba_b),
            self.o_tri_rgba_c.eq(self.i_tri_rgba_c),
            self.o_pnt_xy.eq(self.i_pnt_xy),
            self.o_edge_ab.eq(self.i_edge_ab),
            self.o_edge_bc.eq(self.i_edge_bc),
            self.o_edge_ca.eq(self.i_edge_ca),
            self.o_tri_area.eq(self.i_tri_area),
        ]

        return m


class FragmentZTransform(Elaboratable):
    def __init__(self):
        self.i_tri_xy_a   = Signal(32)
        self.i_tri_xy_b   = Signal(32)
        self.i_tri_xy_c   = Signal(32)
        self.i_tri_rgba_a = Signal(32)
        self.i_tri_rgba_b = Signal(32)
        self.i_tri_rgba_c = Signal(32)
        self.i_pnt_xy     = Signal(32)
        self.i_pnt_wz     = Signal(32)
        self.i_valid      = Signal()

        self.i_edge_ab   = Signal(signed(32))
        self.i_edge_bc   = Signal(signed(32))
        self.i_edge_ca   = Signal(signed(32))
        self.i_tri_area  = Signal(signed(32))

        self.o_tri_xy_a   = Signal(32)
        self.o_tri_xy_b   = Signal(32)
        self.o_tri_xy_c   = Signal(32)
        self.o_tri_rgba_a = Signal(32)
        self.o_tri_rgba_b = Signal(32)
        self.o_tri_rgba_c = Signal(32)
        self.o_pnt_xy     = Signal(32)
        self.o_pnt_z      = Signal(32)
        self.o_valid      = Signal()

        self.o_edge_ab   = Signal(signed(32))
        self.o_edge_bc   = Signal(signed(32))
        self.o_edge_ca   = Signal(signed(32))
        self.o_tri_area  = Signal(signed(32))        

    def elaborate(self, _):
        m = Module()

        # Division is misery.
        #
        # See: https://en.wikipedia.org/wiki/Division_algorithm#Non-restoring_division
        remainder = [Signal(64) for _ in range(33)]
        denominator = [Signal(64) for _ in range(33)]
        quotient = [Signal(32) for _ in range(33)]

        m.d.sync += [
            remainder[32].eq(1 << 31), # 1.0 as numerator
            denominator[32].eq(self.i_pnt_wz << 32),
            quotient[32].eq(0)
        ]

        for i in range(32, 0, -1):
            non_negative = remainder[i] >= 0
            with m.If(non_negative):
                m.d.sync += [
                    quotient[i-1].eq(quotient[i].shift_left(1) | non_negative),
                    remainder[i-1].eq(remainder[i].shift_left(1) - denominator[i]),
                ]
            with m.Else():
                m.d.sync += [
                    quotient[i-1].eq(quotient[i].shift_left(1) | non_negative),
                    remainder[i-1].eq(remainder[i].shift_left(1) + denominator[i]),
                ]
            m.d.sync += denominator[i-1].eq(denominator[i])

        m.d.sync += self.o_pnt_z.eq(quotient[0] - ~quotient[0])

        return m


if __name__ == "__main__":
    from amaranth.sim import *

    fitt = FragmentInTriangleTest()

    def test():
        def edge(ax, ay, bx, by, cx, cy): # ax, ay, bx, by, cx, cy all Q12.4
            x = (((cx - ax) * (by - ay)) - ((cy - ay) * (bx - ax))) >> 4 # Q24.4
            x -= int((ax < bx or (ax == bx and by < ay)))
            return x

        a_x, a_y = 0x0949, 0x0449
        b_x, b_y = 0x1EB6, 0x19B6
        c_x, c_y = 0x0949, 0x19B6

        canvas = [[0 for _ in range(512)] for _ in range(512)]

        yield fitt.i_tri_xy_b.eq(Cat(C(b_x, 16), C(b_y, 16)))
        yield fitt.i_tri_xy_a.eq(Cat(C(a_x, 16), C(a_y, 16)))
        yield fitt.i_tri_xy_c.eq(Cat(C(c_x, 16), C(c_y, 16)))

        for y in range(512):
            for x in range(512):
                yield fitt.i_point.eq(Cat(C(x << 4, 16), C(y << 4, 16)))
                yield fitt.i_edge_ab.eq(edge(a_x, a_y, b_x, b_y, x << 4, y << 4))
                yield fitt.i_edge_bc.eq(edge(b_x, b_y, c_x, c_y, x << 4, y << 4))
                yield fitt.i_edge_ca.eq(edge(c_x, c_y, a_x, a_y, x << 4, y << 4))
                yield fitt.i_tri_area.eq(edge(a_x, a_y, b_x, b_y, c_x, c_y))
                yield fitt.i_valid.eq(1)

                yield

                valid = yield fitt.o_valid
                if valid:
                    canvas[y][x] = 1
        
        with open("triangle.ppm", "w") as f:
            f.write("P1\n")
            f.write("512 512\n")
            for y in range(0, 512):
                for x in range(0, 512):
                    if canvas[y][x] == 1:
                        f.write("{} ".format(1))
                    else:
                        f.write("{} ".format(0))
                f.write("\n")

    sim = Simulator(fitt)
    sim.add_clock(1e-9)
    sim.add_sync_process(test)
    with sim.write_vcd("test.vcd", "test.gtkw"):
        sim.run()

