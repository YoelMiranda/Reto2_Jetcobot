function DH = dh_jetcobot()
% DH_JETCOBOT  Tabla Denavit-Hartenberg ESTANDAR del JetCobot (MyCobot 280).
%   Cada fila i:  [ theta_offset(rad)  d(mm)  a(mm)  alpha(rad) ]
%   theta_i = q_i + theta_offset_i     (q_i = angulo de la articulacion i)
%
%   T_i-1,i = Rz(theta) * Tz(d) * Tx(a) * Rx(alpha)
%
%   Longitudes: cotas del PPT (135~131.22, 110~110.4, 96, 75~75.05) y hoja de datos.
%   d6 = 53.7 mm = 45.6 (hoja de datos) + ~8 mm calibrados contra get_coords()
%   (error inicial max 12.9 mm -> 7.1 mm tras calibrar; ver RB2_item1_evidencia.md).
    d1 = 131.22;  a2 = -110.4;  a3 = -96.0;
    d4 = 63.40;   d5 = 75.05;   d6 = 53.70;

    %        theta_off   d    a    alpha
    DH = [    0         d1    0     pi/2 ;   % J1: base, gira sobre Z vertical
             -pi/2      0     a2    0    ;   % J2: hombro
              0         0     a3    0    ;   % J3: codo
             -pi/2      d4    0     pi/2 ;   % J4: muneca 1
              pi/2      d5    0    -pi/2 ;   % J5: muneca 2
              0         d6    0     0    ];  % J6: muneca 3 / punto que reporta el firmware
end
