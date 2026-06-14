// posit_fused_butterfly.v — Fused decode-compute-encode butterfly
// Uses only 6 decoders + 4 encoders instead of 20 decoders + 10 encoders
module posit_fused_butterfly #(parameter N = 11)(
    input  [N-1:0] ar, ai,
    input  [N-1:0] br, bi,
    input  [N-1:0] wr, wi,
    output [N-1:0] y0r, y0i,
    output [N-1:0] y1r, y1i
);

localparam MW = N;  // internal mantissa width

// ==================== STAGE 1: DECODE 6 INPUTS ====================
wire s_ar, s_ai, s_br, s_bi, s_wr, s_wi;
wire signed [5:0] k_ar, k_ai, k_br, k_bi, k_wr, k_wi;
wire e_ar, e_ai, e_br, e_bi, e_wr, e_wi;
wire [N-4:0] f_ar, f_ai, f_br, f_bi, f_wr, f_wi;

posit_decode #(.N(N)) D_ar (.p(ar), .sign(s_ar), .k(k_ar), .exp(e_ar), .frac(f_ar));
posit_decode #(.N(N)) D_ai (.p(ai), .sign(s_ai), .k(k_ai), .exp(e_ai), .frac(f_ai));
posit_decode #(.N(N)) D_br (.p(br), .sign(s_br), .k(k_br), .exp(e_br), .frac(f_br));
posit_decode #(.N(N)) D_bi (.p(bi), .sign(s_bi), .k(k_bi), .exp(e_bi), .frac(f_bi));
posit_decode #(.N(N)) D_wr (.p(wr), .sign(s_wr), .k(k_wr), .exp(e_wr), .frac(f_wr));
posit_decode #(.N(N)) D_wi (.p(wi), .sign(s_wi), .k(k_wi), .exp(e_wi), .frac(f_wi));

// Convert decoded fields to internal format
// scale = 2*k + exp, mant = {1, frac} padded to MW bits
wire signed [6:0] sc_ar, sc_ai, sc_br, sc_bi, sc_wr, sc_wi;
wire [N-3:0] mt_ar, mt_ai, mt_br, mt_bi, mt_wr, mt_wi;  // N-2 bit mantissa {1,frac}
wire z_ar, z_ai, z_br, z_bi, z_wr, z_wi;
wire n_ar, n_ai, n_br, n_bi, n_wr, n_wi;

assign sc_ar = (k_ar <<< 1) + e_ar;  assign mt_ar = {1'b1, f_ar};
assign sc_ai = (k_ai <<< 1) + e_ai;  assign mt_ai = {1'b1, f_ai};
assign sc_br = (k_br <<< 1) + e_br;  assign mt_br = {1'b1, f_br};
assign sc_bi = (k_bi <<< 1) + e_bi;  assign mt_bi = {1'b1, f_bi};
assign sc_wr = (k_wr <<< 1) + e_wr;  assign mt_wr = {1'b1, f_wr};
assign sc_wi = (k_wi <<< 1) + e_wi;  assign mt_wi = {1'b1, f_wi};

assign z_ar = (ar == 0);  assign n_ar = (ar == (1 << (N-1)));
assign z_ai = (ai == 0);  assign n_ai = (ai == (1 << (N-1)));
assign z_br = (br == 0);  assign n_br = (br == (1 << (N-1)));
assign z_bi = (bi == 0);  assign n_bi = (bi == (1 << (N-1)));
assign z_wr = (wr == 0);  assign n_wr = (wr == (1 << (N-1)));
assign z_wi = (wi == 0);  assign n_wi = (wi == (1 << (N-1)));

// ==================== STAGE 2: 4 RAW MULTIPLIES ====================
// M1 = br * wr,  M2 = bi * wi,  M3 = br * wi,  M4 = bi * wr
wire sm1,sm2,sm3,sm4;
wire signed [6:0] scm1,scm2,scm3,scm4;
wire [MW-1:0] mm1,mm2,mm3,mm4;
wire zm1,zm2,zm3,zm4, nm1,nm2,nm3,nm4;

posit_mul_raw #(.N(N),.MW(MW)) M1 (
    .sign_a(s_br),.scale_a(sc_br),.mant_a(mt_br),.zero_a(z_br),.nar_a(n_br),
    .sign_b(s_wr),.scale_b(sc_wr),.mant_b(mt_wr),.zero_b(z_wr),.nar_b(n_wr),
    .sign_o(sm1),.scale_o(scm1),.mant_o(mm1),.zero_o(zm1),.nar_o(nm1)
);
posit_mul_raw #(.N(N),.MW(MW)) M2 (
    .sign_a(s_bi),.scale_a(sc_bi),.mant_a(mt_bi),.zero_a(z_bi),.nar_a(n_bi),
    .sign_b(s_wi),.scale_b(sc_wi),.mant_b(mt_wi),.zero_b(z_wi),.nar_b(n_wi),
    .sign_o(sm2),.scale_o(scm2),.mant_o(mm2),.zero_o(zm2),.nar_o(nm2)
);
posit_mul_raw #(.N(N),.MW(MW)) M3 (
    .sign_a(s_br),.scale_a(sc_br),.mant_a(mt_br),.zero_a(z_br),.nar_a(n_br),
    .sign_b(s_wi),.scale_b(sc_wi),.mant_b(mt_wi),.zero_b(z_wi),.nar_b(n_wi),
    .sign_o(sm3),.scale_o(scm3),.mant_o(mm3),.zero_o(zm3),.nar_o(nm3)
);
posit_mul_raw #(.N(N),.MW(MW)) M4 (
    .sign_a(s_bi),.scale_a(sc_bi),.mant_a(mt_bi),.zero_a(z_bi),.nar_a(n_bi),
    .sign_b(s_wr),.scale_b(sc_wr),.mant_b(mt_wr),.zero_b(z_wr),.nar_b(n_wr),
    .sign_o(sm4),.scale_o(scm4),.mant_o(mm4),.zero_o(zm4),.nar_o(nm4)
);

// ==================== STAGE 3: Tr = M1 - M2,  Ti = M3 + M4 ====================
wire s_tr, s_ti;
wire signed [6:0] sc_tr, sc_ti;
wire [MW-1:0] m_tr, m_ti;
wire z_tr, z_ti, n_tr, n_ti;

posit_addsub_raw #(.N(N),.MW(MW)) SUB_Tr (
    .sign_a(sm1),.scale_a(scm1),.mant_a(mm1),.zero_a(zm1),.nar_a(nm1),
    .sign_b(sm2),.scale_b(scm2),.mant_b(mm2),.zero_b(zm2),.nar_b(nm2),
    .do_sub(1'b1),
    .sign_o(s_tr),.scale_o(sc_tr),.mant_o(m_tr),.zero_o(z_tr),.nar_o(n_tr)
);
posit_addsub_raw #(.N(N),.MW(MW)) ADD_Ti (
    .sign_a(sm3),.scale_a(scm3),.mant_a(mm3),.zero_a(zm3),.nar_a(nm3),
    .sign_b(sm4),.scale_b(scm4),.mant_b(mm4),.zero_b(zm4),.nar_b(nm4),
    .do_sub(1'b0),
    .sign_o(s_ti),.scale_o(sc_ti),.mant_o(m_ti),.zero_o(z_ti),.nar_o(n_ti)
);

// ==================== STAGE 4: y0=A+T, y1=A-T ====================
// Convert A inputs to MW-width mantissa (pad with zeros)
wire [MW-1:0] mw_ar, mw_ai;
assign mw_ar = {mt_ar, {(MW-(N-2)){1'b0}}};
assign mw_ai = {mt_ai, {(MW-(N-2)){1'b0}}};

wire s_y0r,s_y0i,s_y1r,s_y1i;
wire signed [6:0] sc_y0r,sc_y0i,sc_y1r,sc_y1i;
wire [MW-1:0] m_y0r,m_y0i,m_y1r,m_y1i;
wire z_y0r,z_y0i,z_y1r,z_y1i, n_y0r,n_y0i,n_y1r,n_y1i;

posit_addsub_raw #(.N(N),.MW(MW)) ADD_y0r (
    .sign_a(s_ar),.scale_a(sc_ar),.mant_a(mw_ar),.zero_a(z_ar),.nar_a(n_ar),
    .sign_b(s_tr),.scale_b(sc_tr),.mant_b(m_tr),.zero_b(z_tr),.nar_b(n_tr),
    .do_sub(1'b0),
    .sign_o(s_y0r),.scale_o(sc_y0r),.mant_o(m_y0r),.zero_o(z_y0r),.nar_o(n_y0r)
);
posit_addsub_raw #(.N(N),.MW(MW)) ADD_y0i (
    .sign_a(s_ai),.scale_a(sc_ai),.mant_a(mw_ai),.zero_a(z_ai),.nar_a(n_ai),
    .sign_b(s_ti),.scale_b(sc_ti),.mant_b(m_ti),.zero_b(z_ti),.nar_b(n_ti),
    .do_sub(1'b0),
    .sign_o(s_y0i),.scale_o(sc_y0i),.mant_o(m_y0i),.zero_o(z_y0i),.nar_o(n_y0i)
);
posit_addsub_raw #(.N(N),.MW(MW)) SUB_y1r (
    .sign_a(s_ar),.scale_a(sc_ar),.mant_a(mw_ar),.zero_a(z_ar),.nar_a(n_ar),
    .sign_b(s_tr),.scale_b(sc_tr),.mant_b(m_tr),.zero_b(z_tr),.nar_b(n_tr),
    .do_sub(1'b1),
    .sign_o(s_y1r),.scale_o(sc_y1r),.mant_o(m_y1r),.zero_o(z_y1r),.nar_o(n_y1r)
);
posit_addsub_raw #(.N(N),.MW(MW)) SUB_y1i (
    .sign_a(s_ai),.scale_a(sc_ai),.mant_a(mw_ai),.zero_a(z_ai),.nar_a(n_ai),
    .sign_b(s_ti),.scale_b(sc_ti),.mant_b(m_ti),.zero_b(z_ti),.nar_b(n_ti),
    .do_sub(1'b1),
    .sign_o(s_y1i),.scale_o(sc_y1i),.mant_o(m_y1i),.zero_o(z_y1i),.nar_o(n_y1i)
);

// ==================== STAGE 5: ENCODE 4 OUTPUTS ====================
posit_raw_to_enc #(.N(N),.MW(MW)) E0r (.sign_i(s_y0r),.scale_i(sc_y0r),.mant_i(m_y0r),.zero_i(z_y0r),.nar_i(n_y0r),.p(y0r));
posit_raw_to_enc #(.N(N),.MW(MW)) E0i (.sign_i(s_y0i),.scale_i(sc_y0i),.mant_i(m_y0i),.zero_i(z_y0i),.nar_i(n_y0i),.p(y0i));
posit_raw_to_enc #(.N(N),.MW(MW)) E1r (.sign_i(s_y1r),.scale_i(sc_y1r),.mant_i(m_y1r),.zero_i(z_y1r),.nar_i(n_y1r),.p(y1r));
posit_raw_to_enc #(.N(N),.MW(MW)) E1i (.sign_i(s_y1i),.scale_i(sc_y1i),.mant_i(m_y1i),.zero_i(z_y1i),.nar_i(n_y1i),.p(y1i));

endmodule
