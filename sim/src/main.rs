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

#[derive(Debug, Clone, Copy)]
struct Q16p16(i16);

impl Q16p16 {
    pub fn one() -> Self {
        Q16p16(1 << 8)
    }

    pub fn div_q24p4(lhs: Q24p4, rhs: Q24p4) -> Q16p16 {
        Q16p16((lhs.0 as f32 / rhs.0 as f32 * (1 << 8) as f32) as i16)
    }
}

impl From<Q24p4> for Q16p16 {
    fn from(val: Q24p4) -> Self {
        Q16p16((val.0 as i16) << 4)
    }
}

impl From<Q12p4> for Q16p16 {
    fn from(val: Q12p4) -> Self {
        Q16p16(val.0 << 4)
    }
}

impl Add<Q16p16> for Q16p16 {
    type Output = Q16p16;

    fn add(self, rhs: Self) -> Self::Output {
        Q16p16(self.0 + rhs.0)
    }
}

// temporary multiplication implementation for testing, looses precision
impl Mul for Q16p16 {
    type Output = Q16p16;

    fn mul(self, rhs: Self) -> Self::Output {
        Q16p16(((self.0 as i64 * rhs.0 as i64) >> 8) as i16)
    }
}

// temporary division implementation for testing
impl Div<Q16p16> for Q16p16 {
    type Output = Q16p16;

    fn div(self, rhs: Self) -> Self::Output {
        Q16p16((self.0 as f32 / rhs.0 as f32 * (1 << 8) as f32) as i16)
    }
}

// temporary division implementation for testing
impl Div<Q24p4> for Q16p16 {
    type Output = Q16p16;

    fn div(self, rhs: Q24p4) -> Self::Output {
        Q16p16((self.0 as f32 / rhs.0 as f32 * 16.0) as i16)
    }
}

// temporary division implementation for testing
impl Div<Q12p4> for Q16p16 {
    type Output = Q16p16;

    fn div(self, rhs: Q12p4) -> Self::Output {
        Q16p16((self.0 as f32 / rhs.0 as f32 * 16.0) as i16)
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
    depth: Q16p16,
    interp_a: Q16p16,
    interp_b: Q16p16,
    interp_c: Q16p16,
}

impl Fragment {
    pub fn new() -> Self {
        Self {
            x: [Q12p4(0); 4],
            y: [Q12p4(0); 4],
            valid: [false; 4],
            depth: Q16p16(0),
            interp_a: Q16p16(0),
            interp_b: Q16p16(0),
            interp_c: Q16p16(0),
        }
    }
}

#[derive(Debug)]
struct Gpu {
    // i_xy_a:
    a_x: Q12p4,
    a_y: Q12p4,
    a_inv_z: Q16p16,
    // i_xy_b:
    b_x: Q12p4,
    b_y: Q12p4,
    b_inv_z: Q16p16,
    // i_xy_c:
    c_x: Q12p4,
    c_y: Q12p4,
    c_inv_z: Q16p16,

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

        let interp_a = self.edge_bc + self.edge_bc_dx * Q12p4::half() + self.edge_bc_dy * Q12p4::half();
        let interp_b = self.edge_ca + self.edge_ca_dx * Q12p4::half() + self.edge_ca_dy * Q12p4::half();
        let interp_c = self.edge_ab + self.edge_ab_dx * Q12p4::half() + self.edge_ab_dy * Q12p4::half();

        frag.interp_a = Q16p16::div_q24p4(interp_a, self.total_area);
        frag.interp_b = Q16p16::div_q24p4(interp_b, self.total_area);
        frag.interp_c = Q16p16::div_q24p4(interp_c, self.total_area);

        frag.depth = Q16p16::one() / (frag.interp_a * self.a_inv_z + frag.interp_b * self.b_inv_z + frag.interp_c * self.c_inv_z);
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

struct Vertex {
    x: Q12p4,
    y: Q12p4,
    z: Q12p4,
    red: u8,
    green: u8,
    blue: u8,
}

fn blit_triangle(framebuffer: &mut [u8; 512*512*3], a: Vertex, b: Vertex, c: Vertex) {
    let start_x = a.x.min(b.x).min(c.x);
    let start_y = a.y.min(b.y).min(c.y);
    let stop_x = a.x.max(b.x).max(c.x);
    let stop_y = a.y.max(b.y).max(c.y);

    let mut gpu = dbg!(Gpu {
        a_x: a.x,
        a_y: a.y,
        a_inv_z: Q16p16::one() / a.z,
        b_x: b.x,
        b_y: b.y,
        b_inv_z: Q16p16::one() / b.z,
        c_x: c.x,
        c_y: c.y,
        c_inv_z: Q16p16::one() / c.z,
        start_x,
        start_y,
        stop_x,
        stop_y,
        edge_ab: Q24p4::edge_function(a.x, a.y, b.x, b.y, start_x + Q12p4::half(), start_y + Q12p4::half()),
        edge_bc: Q24p4::edge_function(b.x, b.y, c.x, c.y, start_x + Q12p4::half(), start_y + Q12p4::half()),
        edge_ca: Q24p4::edge_function(c.x, c.y, a.x, a.y, start_x + Q12p4::half(), start_y + Q12p4::half()),
        total_area: Q24p4::edge_function(a.x, a.y, b.x, b.y, c.x, c.y),
        edge_ab_dx: b.y - a.y,
        edge_ab_dy: a.x - b.x,
        edge_bc_dx: c.y - b.y,
        edge_bc_dy: b.x - c.x,
        edge_ca_dx: a.y - c.y,
        edge_ca_dy: c.x - a.x,
        x: start_x + Q12p4::half(),
        y: start_y + Q12p4::half(),
        x_inc: Q12p4::one(),
        drawing: true,
    });

    // this color interpolation is not implemented as it would be in hardware
    // it is purely so we can see the results of frag.interp_...
    let a_red = a.red as f32 / (a.z.0 as f32 / 16.0);
    let a_green = a.green as f32 / (a.z.0 as f32 / 16.0);
    let a_blue = a.blue as f32 / (a.z.0 as f32 / 16.0);

    let b_red = b.red as f32 / (b.z.0 as f32 / 16.0);
    let b_green = b.green as f32 / (b.z.0 as f32 / 16.0);
    let b_blue = b.blue as f32 / (b.z.0 as f32 / 16.0);

    let c_red = c.red as f32 / (c.z.0 as f32 / 16.0);
    let c_green = c.green as f32 / (c.z.0 as f32 / 16.0);
    let c_blue = c.blue as f32 / (c.z.0 as f32 / 16.0);

    println!("now drawing");
    let mut steps = 0;
    while gpu.drawing {
        steps += 1;
        let frag = gpu.step_rasteriser();
        for pixel in 0..=3 {
            if frag.valid[pixel] {
                let x = frag.x[pixel].truncate() as usize;
                let y = frag.y[pixel].truncate() as usize;
                let interp_a = frag.interp_a.0 as f32 / (1 << 8) as f32;
                let interp_b = frag.interp_b.0 as f32 / (1 << 8) as f32;
                let interp_c = frag.interp_c.0 as f32 / (1 << 8) as f32;
                framebuffer[512*3*y + 3*x + 0] = (a_red * interp_a + b_red * interp_b + c_red * interp_c).clamp(0.0, 255.0) as u8;
                framebuffer[512*3*y + 3*x + 1] = (a_green * interp_a + b_green * interp_b + c_green * interp_c).clamp(0.0, 255.0) as u8;
                framebuffer[512*3*y + 3*x + 2] = (a_blue * interp_a + b_blue * interp_b + c_blue * interp_c).clamp(0.0, 255.0) as u8;
                //println!("hi");
            }
        }
    }
    println!("done, took {} steps", steps);
}


fn main() {
    let mut framebuffer = [255u8; 512*512*3];

    let a = Vertex {
        x: Q12p4(0x0949),
        y: Q12p4(0x0449),
        z: Q12p4::one(),
        red: 0,
        green: 0,
        blue: 255,
    };
    let b = Vertex {
        x: Q12p4(0x1EB6),
        y: Q12p4(0x19B6),
        z: Q12p4::two(),
        red: 255,
        green: 0,
        blue: 0,
    };
    let c = Vertex {
        x: Q12p4(0x0949),
        y: Q12p4(0x19B6),
        z: Q12p4::one(),
        red: 0,
        green: 255,
        blue: 0,
    };
    blit_triangle(&mut framebuffer, a, b, c);

    let b = Vertex {
        x: Q12p4(0x0949),
        y: Q12p4(0x0449),
        z: Q12p4::one(),
        red: 0,
        green: 0,
        blue: 255,
    };
    let a = Vertex {
        x: Q12p4(0x1EB6),
        y: Q12p4(0x19B6),
        z: Q12p4::two(),
        red: 255,
        green: 0,
        blue: 0,
    };
    let c = Vertex {
        x: Q12p4(0x1EB6),
        y: Q12p4(0x0449),
        z: Q12p4::two(),
        red: 255,
        green: 255,
        blue: 0,
    };
    blit_triangle(&mut framebuffer, a, b, c);

    let mut f = std::fs::File::create("triangle.ppm").unwrap();
    writeln!(f, "P6").unwrap();
    writeln!(f, "512 512").unwrap();
    writeln!(f, "255").unwrap();
    f.write_all(&framebuffer).unwrap();
}
