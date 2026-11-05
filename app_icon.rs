//! Poly Studio mark, shared by desktop, packaging and CLI. The logo is stored once as a 512 px
//! RGBA master (`poly_mark_512.rgba`, straight alpha) and resampled to any size from 1 to 2048.

const MASTER: usize = 512;
static MASTER_RGBA: &[u8] = include_bytes!("poly_mark_512.rgba");

/// One master pixel as premultiplied RGBA (0..=1 alpha, colour scaled by it); out-of-range
/// coordinates clamp to the edge.
fn px(x: usize, y: usize) -> [f32; 4] {
    let i = (y.min(MASTER - 1) * MASTER + x.min(MASTER - 1)) * 4;
    let g = |k: usize| f32::from(MASTER_RGBA.get(i + k).copied().unwrap_or(0));
    let a = g(3) / 255.0;
    [g(0) * a, g(1) * a, g(2) * a, a]
}

/// The icon at `size` x `size`, straight-alpha RGBA, rows top to bottom.
pub fn rgba(size: usize) -> Result<Vec<u8>, String> {
    if !(1..=2048).contains(&size) {
        return Err("icon size must be 1..=2048".into());
    }
    if MASTER_RGBA.len() != MASTER * MASTER * 4 {
        return Err("icon master has the wrong length".into());
    }
    let scale = MASTER as f32 / size as f32;
    let mut out = Vec::with_capacity(size * size * 4);
    for y in 0..size {
        let y0 = (y as f32 * scale).floor() as usize;
        let y1 = (((y + 1) as f32 * scale).ceil() as usize).max(y0 + 1);
        for x in 0..size {
            let x0 = (x as f32 * scale).floor() as usize;
            let x1 = (((x + 1) as f32 * scale).ceil() as usize).max(x0 + 1);
            let mut sum = [0.0f32; 4];
            let mut n = 0.0f32;
            for yy in y0..y1 {
                for xx in x0..x1 {
                    let p = px(xx, yy);
                    for (acc, v) in sum.iter_mut().zip(p) {
                        *acc += v;
                    }
                    n += 1.0;
                }
            }
            let a = sum[3] / n;
            if a <= 0.0 {
                out.extend_from_slice(&[0, 0, 0, 0]);
            } else {
                // un-premultiply: sum[c] / n is colour * alpha, so divide by the mean alpha
                for c in sum.iter().take(3) {
                    out.push(((c / n) / a).round().clamp(0.0, 255.0) as u8);
                }
                out.push((a * 255.0).round().clamp(0.0, 255.0) as u8);
            }
        }
    }
    Ok(out)
}
