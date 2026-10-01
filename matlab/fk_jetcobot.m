function [T, p, Tacum] = fk_jetcobot(q)
% FK_JETCOBOT  Cinematica directa del JetCobot (DH estandar).
%   q      : 1x6 o 6x1, angulos articulares en RADIANES (como /joint_states)
%   T      : matriz homogenea 4x4 base -> efector (flange)
%   p      : posicion [x y z] en mm respecto a la base
%   Tacum  : 4x4x7, Tacum(:,:,k+1) = T_0k  (k = 0..6), para graficar frames
    q  = q(:).';
    if numel(q) ~= 6
        error('fk_jetcobot:q', 'Se esperaban 6 angulos, llegaron %d', numel(q));
    end
    DH = dh_jetcobot();
    T = eye(4);
    Tacum = zeros(4,4,7);  Tacum(:,:,1) = T;
    for i = 1:6
        th = q(i) + DH(i,1);   d = DH(i,2);   a = DH(i,3);   al = DH(i,4);
        ct = cos(th); st = sin(th); ca = cos(al); sa = sin(al);
        Ti = [ ct, -st*ca,  st*sa, a*ct;
               st,  ct*ca, -ct*sa, a*st;
               0,      sa,     ca,    d;
               0,       0,      0,    1 ];
        T = T * Ti;
        Tacum(:,:,i+1) = T;
    end
    p = T(1:3,4).';
end
