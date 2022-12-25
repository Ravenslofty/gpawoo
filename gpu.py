from amaranth import *

class TriangleRender(Elaboratable):
    def __init__(self):
        self.i_xy_a  = Signal(32)
        self.i_xy_b  = Signal(32)
        self.i_xy_c  = Signal(32)

        self.o_xy    = Signal(32)
        self.o_valid = Signal()
        self.o_done  = Signal()

    def elaborate(self, platform):
        m = Module()

        # 12.4 fixed-point
        a_x, a_y = self.i_xy_a[0:16], self.i_xy_a[16:32]
        b_x, b_y = self.i_xy_b[0:16], self.i_xy_b[16:32]
        c_x, c_y = self.i_xy_c[0:16], self.i_xy_c[16:32]
        start_x = Mux(a_x < b_x, Mux(a_x < c_x, a_x, c_x), Mux(b_x < c_x, b_x, c_x))
        start_y = Mux(a_y < b_y, Mux(a_y < c_y, a_y, c_y), Mux(b_y < c_y, b_y, c_y))
        stop_x  = Mux(a_x > b_x, Mux(a_x > c_x, a_x, c_x), Mux(b_x > c_x, b_x, c_x))
        stop_y  = Mux(a_y > b_y, Mux(a_y > c_y, a_y, c_y), Mux(b_y > c_y, b_y, c_y))
        x       = Signal(16)
        y       = Signal(16)

        edge_ab_dx = Signal(signed(16))
        edge_ab_dy = Signal(signed(16))
        edge_ab    = Signal(signed(32))
        edge_bc_dx = Signal(signed(16))
        edge_bc_dy = Signal(signed(16))
        edge_bc    = Signal(signed(32))
        edge_ca_dx = Signal(signed(16))
        edge_ca_dy = Signal(signed(16))
        edge_ca    = Signal(signed(32))

        with m.FSM():
            with m.State("WAIT1"):
                m.next = "WAIT2"
            with m.State("WAIT2"):
                m.d.sync += [
                    x.eq(start_x + (1 << 3)),
                    y.eq(start_y + (1 << 3)),
                ]
                m.next = "SETUP"
                
            with m.State("SETUP"):
                def edge(ax, ay, bx, by, cx, cy): # ax, ay, bx, by, cx, cy all Q12.4
                    return (((cx - ax) * (by - ay)) - ((cy - ay) * (bx - ax))) >> 4 # Q24.4
                m.d.sync += [
                    edge_ab_dx.eq(b_x - a_x),
                    edge_ab_dy.eq(b_y - a_y),
                    edge_ab.eq(edge(a_x, a_y, b_x, b_y, x, y)),
                    edge_bc_dx.eq(c_x - b_x),
                    edge_bc_dy.eq(c_y - b_y),
                    edge_bc.eq(edge(b_x, b_y, c_x, c_y, x, y)),
                    edge_ca_dx.eq(a_x - c_x),
                    edge_ca_dy.eq(a_y - c_y),
                    edge_ca.eq(edge(c_x, c_y, a_x, a_y, x, y)),
                ]
                m.next = "FORWARDS"

            with m.State("FORWARDS"):
                m.d.sync += [
                    self.o_xy.eq(Cat(x, y)),
                    self.o_valid.eq(Cat(edge_ab >= 0, edge_bc >= 0, edge_ca >= 0).all() | Cat(edge_ab <= 0, edge_bc <= 0, edge_ca <= 0).all()),
                    edge_ab.eq(edge_ab + edge_ab_dy),
                    edge_bc.eq(edge_bc + edge_bc_dy),
                    edge_ca.eq(edge_ca + edge_ca_dy),
                    x.eq(x + (1 << 4)),
                ]
                with m.If((x + (1 << 4)) > stop_x):
                    m.d.sync += [
                        edge_ab.eq(edge_ab - edge_ab_dx + edge_ab_dy),
                        edge_bc.eq(edge_bc - edge_bc_dx + edge_bc_dy),
                        edge_ca.eq(edge_ca - edge_ca_dx + edge_ca_dy),
                    ]
                    with m.If((y + (1 << 4)) > stop_y):
                        m.next = "DONE"
                    with m.Else():
                        m.d.sync += y.eq(y + (1 << 4))
                        m.next = "BACKWARDS"

            with m.State("BACKWARDS"):
                m.d.sync += [
                    self.o_xy.eq(Cat(x, y)),
                    self.o_valid.eq(Cat(edge_ab >= 0, edge_bc >= 0, edge_ca >= 0).all() | Cat(edge_ab <= 0, edge_bc <= 0, edge_ca <= 0).all()),
                    edge_ab.eq(edge_ab - edge_ab_dy),
                    edge_bc.eq(edge_bc - edge_bc_dy),
                    edge_ca.eq(edge_ca - edge_ca_dy),
                    x.eq(x - (1 << 4)),
                ]
                with m.If(x <= start_x):
                    m.d.sync += [
                        edge_ab.eq(edge_ab - edge_ab_dx - edge_ab_dy),
                        edge_bc.eq(edge_bc - edge_bc_dx - edge_bc_dy),
                        edge_ca.eq(edge_ca - edge_ca_dx - edge_ca_dy),
                    ]
                    with m.If((y + (1 << 4)) > stop_y):
                        m.next = "DONE"
                    with m.Else():
                        m.d.sync += y.eq(y + (1 << 4))
                        m.next = "FORWARDS"

            with m.State("DONE"):
                m.d.sync += self.o_done.eq(1)

        return m


if __name__ == "__main__":
    from amaranth.sim import *

    tr = TriangleRender()
    ports = [tr.i_xy_a, tr.i_xy_b, tr.i_xy_c, tr.o_xy, tr.o_valid]

    def test():
        yield tr.i_xy_a.eq(0x19B61EB6)
        yield tr.i_xy_b.eq(0x04490949)
        yield tr.i_xy_c.eq(0x19B60949)
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