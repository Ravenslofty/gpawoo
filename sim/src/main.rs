use std::fmt::Display;
use std::ops::{Add, AddAssign, Shl, Neg, Sub, Mul, Div};
use std::io::Write;

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
struct Q12p4(i16);

impl Q12p4 {
    pub fn half() -> Self {
        Self(1 << 3)
    }

    pub fn zero() -> Self {
        Self(0)
    }

    pub fn one() -> Self {
        Self(1 << 4)
    }

    pub fn two() -> Self {
        Self(2 << 4)
    }

    pub fn is_positive(self) -> bool {
        self.0 > 0
    }

    pub fn is_zero(self) -> bool {
        self.0 == 0
    }

    pub fn is_negative(self) -> bool {
        self.0 < 0
    }

    pub fn truncate(self) -> i16 {
        self.0 >> 4
    }
}

impl Add for Q12p4 {
    type Output = Q12p4;

    fn add(self, rhs: Self) -> Self::Output {
        Self(self.0 + rhs.0)
    }
}

impl AddAssign<Q12p4> for Q12p4 {
    fn add_assign(&mut self, rhs: Q12p4) {
        self.0 += rhs.0;
    }
}

impl Sub for Q12p4 {
    type Output = Q12p4;

    fn sub(self, rhs: Self) -> Self::Output {
        Self(self.0 - rhs.0)
    }
}

impl Mul for Q12p4 {
    type Output = Q24p4;

    fn mul(self, rhs: Self) -> Self::Output {
        Q24p4((self.0 as i32 * rhs.0 as i32) >> 4)
    }
}

impl Shl<i16> for Q12p4 {
    type Output = Q12p4;

    fn shl(self, rhs: i16) -> Self::Output {
        Self(self.0 << rhs)
    }
}

impl Neg for Q12p4 {
    type Output = Q12p4;

    fn neg(self) -> Self::Output {
        Self(-self.0)
    }
}

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
struct Q24p4(i32);

impl Q24p4 {
    pub fn zero() -> Self {
        Self(0)
    }

    pub fn one() -> Self {
        Self(1 << 4)
    }

    pub fn two() -> Self {
        Self(2 << 4)
    }

    pub fn is_positive(self) -> bool {
        self.0 > 0
    }

    pub fn is_zero(self) -> bool {
        self.0 == 0
    }

    pub fn is_negative(self) -> bool {
        self.0 < 0
    }

    pub fn edge_function(ax: Q12p4, ay: Q12p4, bx: Q12p4, by: Q12p4, px: Q12p4, py: Q12p4) -> Self {
        (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    }
}

impl Add<Q12p4> for Q24p4 {
    type Output = Q24p4;

    fn add(self, rhs: Q12p4) -> Self::Output {
        Self(self.0 + (rhs.0 as i32))
    }
}

impl Add<Q24p4> for Q24p4 {
    type Output = Q24p4;

    fn add(self, rhs: Q24p4) -> Self::Output {
        Self(self.0 + rhs.0)
    }
}

impl AddAssign<Q12p4> for Q24p4 {
    fn add_assign(&mut self, rhs: Q12p4) {
        self.0 += rhs.0 as i32;
    }
}

impl Sub for Q24p4 {
    type Output = Q24p4;

    fn sub(self, rhs: Self) -> Self::Output {
        Self(self.0 - rhs.0)
    }
}

// temporary multiplication implementation for testing, looses precision
impl Mul for Q24p4 {
    type Output = Q24p4;

    fn mul(self, rhs: Self) -> Self::Output {
        Q24p4((self.0 * rhs.0) >> 4)
    }
}

// temporary division implementation for testing
impl Div for Q24p4 {
    type Output = Q24p4;

    fn div(self, rhs: Self) -> Self::Output {
        Q24p4((self.0 as f32 / (rhs.0 as f32 / 16.0)) as i32)
    }
}

// temporary negation implementation for testing
impl Neg for Q24p4 {
    type Output = Q24p4;

    fn neg(self) -> Self::Output {
        Q24p4(-self.0)
    }
}

impl From<Q12p4> for Q24p4 {
    fn from(x: Q12p4) -> Self {
        Self(x.0 as i32)
    }
}

impl Display for Q24p4 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", (self.0 as f64) / 16.0)
    }
}

// 2x2 box of pixels:
// 0 1 -> X
// 2 3
// |
// v
// Y
struct Fragment {
    x: [Q12p4; 4],
    y: [Q12p4; 4],
    valid: [bool; 4],
    depth: Q24p4,
    interp_a: Q24p4,
    interp_b: Q24p4,
    interp_c: Q24p4,
}

impl Fragment {
    pub fn new() -> Self {
        Self {
            x: [Q12p4(0); 4],
            y: [Q12p4(0); 4],
            valid: [false; 4],
            depth: Q24p4(0),
            interp_a: Q24p4(0),
            interp_b: Q24p4(0),
            interp_c: Q24p4(0),
        }
    }
}

#[derive(Debug)]
struct Gpu {
    // i_xy_a:
    a_x: Q12p4,
    a_y: Q12p4,
    a_inv_z: Q24p4,
    // i_xy_b:
    b_x: Q12p4,
    b_y: Q12p4,
    b_inv_z: Q24p4,
    // i_xy_c:
    c_x: Q12p4,
    c_y: Q12p4,
    c_inv_z: Q24p4,

    // i want to precalculate 1 / this, but Q24p4 doesn't have enough precision
    total_area: Q24p4,

    // i_start_x:
    start_x: Q12p4,
    // i_start_y:
    start_y: Q12p4,
    // i_stop_x:
    stop_x: Q12p4,
    // i_stop_y:
    stop_y: Q12p4,

    // i_edge_ab:
    edge_ab: Q24p4,
    // i_edge_bc:
    edge_bc: Q24p4,
    // i_edge_ca:
    edge_ca: Q24p4,

    // i_edge_ab_dx:
    edge_ab_dx: Q12p4,
    // i_edge_ab_dy:
    edge_ab_dy: Q12p4,
    // i_edge_bc_dx:
    edge_bc_dx: Q12p4,
    // i_edge_bc_dy:
    edge_bc_dy: Q12p4,
    // i_edge_ca_dx:
    edge_ca_dx: Q12p4,
    // i_edge_ca_dy:
    edge_ca_dy: Q12p4,
    
    x: Q12p4,
    y: Q12p4,
    x_inc: Q12p4,
    drawing: bool,
}

impl Gpu {
    pub fn step_rasteriser(&mut self) -> Fragment {
        let mut frag = Fragment::new();

        //println!("AB: {}, BC: {}, CA: {}", self.edge_ab, self.edge_bc, self.edge_ca);

        let ok = |edge_ab: Q24p4, edge_bc: Q24p4, edge_ca: Q24p4| {
            let ab_ok = edge_ab.is_negative() || (edge_ab.is_zero() && (self.edge_ab_dy.is_negative() || (self.edge_ab_dy.is_zero() && self.edge_ab_dx.is_negative())));
            let bc_ok = edge_bc.is_negative() || (edge_bc.is_zero() && (self.edge_bc_dy.is_negative() || (self.edge_bc_dy.is_zero() && self.edge_bc_dx.is_negative())));
            let ca_ok = edge_ca.is_negative() || (edge_ca.is_zero() && (self.edge_ca_dy.is_negative() || (self.edge_ca_dy.is_zero() && self.edge_ca_dx.is_negative())));
            ab_ok && bc_ok && ca_ok
        };

        if !self.drawing {
            return frag;
        }

        frag.x[0] = self.x;
        frag.x[1] = self.x + self.x_inc;
        frag.x[2] = self.x;
        frag.x[3] = self.x + self.x_inc;

        frag.y[0] = self.y;
        frag.y[1] = self.y;
        frag.y[2] = self.y + Q12p4::one();
        frag.y[3] = self.y + Q12p4::one();

        frag.valid[0] = ok(self.edge_ab, self.edge_bc, self.edge_ca);
        frag.valid[1] = ok(self.edge_ab + self.edge_ab_dx, self.edge_bc + self.edge_bc_dx, self.edge_ca + self.edge_ca_dx);
        frag.valid[2] = ok(self.edge_ab + self.edge_ab_dy, self.edge_bc + self.edge_bc_dy, self.edge_ca + self.edge_ca_dy);
        frag.valid[3] = ok(self.edge_ab + self.edge_ab_dx + self.edge_ab_dy, self.edge_bc + self.edge_bc_dx + self.edge_bc_dy, self.edge_ca + self.edge_ca_dx + self.edge_ca_dy);

        frag.interp_a = self.edge_bc + self.edge_bc_dx * Q12p4::half() + self.edge_bc_dy * Q12p4::half();
        frag.interp_b = self.edge_ca + self.edge_ca_dx * Q12p4::half() + self.edge_ca_dy * Q12p4::half();
        frag.interp_c = self.edge_ab + self.edge_ab_dx * Q12p4::half() + self.edge_ab_dy * Q12p4::half();

        frag.interp_a = frag.interp_a / self.total_area;
        frag.interp_b = frag.interp_b / self.total_area;
        frag.interp_c = frag.interp_c / self.total_area;

        frag.depth = frag.interp_a * self.a_inv_z + frag.interp_b * self.b_inv_z + frag.interp_c * self.c_inv_z;
        frag.interp_a = frag.interp_a * frag.depth;
        frag.interp_b = frag.interp_b * frag.depth;
        frag.interp_c = frag.interp_c * frag.depth;

        if (self.x_inc.is_positive() && self.x + (self.x_inc << 1) > self.stop_x) || (self.x_inc.is_negative() && self.x + (self.x_inc << 1) <= self.start_x) {
            self.x += self.x_inc << 1;
            self.x_inc = -self.x_inc;
            self.y += Q12p4::two();
            self.edge_ab += (self.edge_ab_dx << 1) + (self.edge_ab_dy << 1);
            self.edge_bc += (self.edge_bc_dx << 1) + (self.edge_bc_dy << 1);
            self.edge_ca += (self.edge_ca_dx << 1) + (self.edge_ca_dy << 1);
            self.edge_ab_dx = -self.edge_ab_dx;
            self.edge_bc_dx = -self.edge_bc_dx;
            self.edge_ca_dx = -self.edge_ca_dx;
        } else {
            self.x += self.x_inc << 1;
            self.edge_ab += self.edge_ab_dx << 1;
            self.edge_bc += self.edge_bc_dx << 1;
            self.edge_ca += self.edge_ca_dx << 1;
        }

        self.drawing = self.y <= self.stop_y;

        frag
    }
}

fn main() {
    let mut framebuffer = vec![255u8; 512*512*3];

    let a_x = Q12p4(0x0949);
    let a_y = Q12p4(0x0449);
    let a_z = Q12p4(0x0010); // 1.0
    let b_x = Q12p4(0x1EB6);
    let b_y = Q12p4(0x19B6);
    let b_z = Q12p4(0x0020); // 2.0
    let c_x = Q12p4(0x0949);
    let c_y = Q12p4(0x19B6); 
    let c_z = Q12p4(0x0010); // 1.0

    let start_x = a_x.min(b_x).min(c_x);
    let start_y = a_y.min(b_y).min(c_y);
    let stop_x = a_x.max(b_x).max(c_x);
    let stop_y = a_y.max(b_y).max(c_y);

    let mut gpu = dbg!(Gpu {
        a_x,
        a_y,
        a_inv_z: Q24p4::one() / a_z.into(),
        b_x,
        b_y,
        b_inv_z: Q24p4::one() / b_z.into(),
        c_x,
        c_y,
        c_inv_z: Q24p4::one() / c_z.into(),
        start_x,
        start_y,
        stop_x,
        stop_y,
        edge_ab: Q24p4::edge_function(a_x, a_y, b_x, b_y, start_x + Q12p4::half(), start_y + Q12p4::half()),
        edge_bc: Q24p4::edge_function(b_x, b_y, c_x, c_y, start_x + Q12p4::half(), start_y + Q12p4::half()),
        edge_ca: Q24p4::edge_function(c_x, c_y, a_x, a_y, start_x + Q12p4::half(), start_y + Q12p4::half()),
        total_area: Q24p4::edge_function(a_x, a_y, b_x, b_y, c_x, c_y),
        edge_ab_dx: b_y - a_y,
        edge_ab_dy: a_x - b_x,
        edge_bc_dx: c_y - b_y,
        edge_bc_dy: b_x - c_x,
        edge_ca_dx: a_y - c_y,
        edge_ca_dy: c_x - a_x,
        x: start_x + Q12p4::half(),
        y: start_y + Q12p4::half(),
        x_inc: Q12p4::one(),
        drawing: true,
    });

    println!("now drawing");
    let mut steps = 0;
    while gpu.drawing {
        steps += 1;
        let frag = gpu.step_rasteriser();
        for pixel in 0..=3 {
            if frag.valid[pixel] {
                let x = frag.x[pixel].truncate() as usize;
                let y = frag.y[pixel].truncate() as usize;
                framebuffer[512*3*y + 3*x + 0] = 0;
                framebuffer[512*3*y + 3*x + 1] = frag.depth.0 as u8 * 15;
                framebuffer[512*3*y + 3*x + 2] = 255;
                //println!("hi");
            }
        }
    }
    println!("done, took {} steps", steps);

    let b_x = Q12p4(0x0949);
    let b_y = Q12p4(0x0449);
    let b_z = Q12p4(0x0010); // 1.0
    let a_x = Q12p4(0x1EB6);
    let a_y = Q12p4(0x19B6);
    let a_z = Q12p4(0x0020); // 2.0
    let c_x = Q12p4(0x1EB6);
    let c_y = Q12p4(0x0449);
    let c_z = Q12p4(0x0020); // 2.0

    let start_x = a_x.min(b_x).min(c_x);
    let start_y = a_y.min(b_y).min(c_y);
    let stop_x = a_x.max(b_x).max(c_x);
    let stop_y = a_y.max(b_y).max(c_y);

    let mut gpu = dbg!(Gpu {
        a_x,
        a_y,
        a_inv_z: Q24p4::one() / a_z.into(),
        b_x,
        b_y,
        b_inv_z: Q24p4::one() / b_z.into(),
        c_x,
        c_y,
        c_inv_z: Q24p4::one() / c_z.into(),
        start_x,
        start_y,
        stop_x,
        stop_y,
        edge_ab: Q24p4::edge_function(a_x, a_y, b_x, b_y, start_x, start_y),
        edge_bc: Q24p4::edge_function(b_x, b_y, c_x, c_y, start_x, start_y),
        edge_ca: Q24p4::edge_function(c_x, c_y, a_x, a_y, start_x, start_y),
        total_area: Q24p4::edge_function(a_x, a_y, b_x, b_y, c_x, c_y),
        edge_ab_dx: b_y - a_y,
        edge_ab_dy: a_x - b_x,
        edge_bc_dx: c_y - b_y,
        edge_bc_dy: b_x - c_x,
        edge_ca_dx: a_y - c_y,
        edge_ca_dy: c_x - a_x,
        x: start_x + Q12p4::half(),
        y: start_y + Q12p4::half(),
        x_inc: Q12p4::one(),
        drawing: true,
    });

    println!("now drawing");
    let mut steps = 0;
    while gpu.drawing {
        steps += 1;
        let frag = gpu.step_rasteriser();
        for pixel in 0..=3 {
            if frag.valid[pixel] {
                let x = frag.x[pixel].truncate() as usize;
                let y = frag.y[pixel].truncate() as usize;
                framebuffer[512*3*y + 3*x + 0] = 255;
                framebuffer[512*3*y + 3*x + 1] = frag.depth.0 as u8 * 15;
                framebuffer[512*3*y + 3*x + 2] = 0;
                //println!("hi");
            }
        }
    }
    println!("done, took {} steps", steps);

    let mut f = std::fs::File::create("triangle.ppm").unwrap();
    writeln!(f, "P6").unwrap();
    writeln!(f, "512 512").unwrap();
    writeln!(f, "255").unwrap();
    f.write_all(&framebuffer).unwrap();
}