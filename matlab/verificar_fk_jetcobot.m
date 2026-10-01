% VERIFICAR_FK_JETCOBOT  Calcula la matriz T del JetCobot y la compara con lo que
% muestra control_joints.ipynb. Un solo archivo, no depende de otros.
%
% USO: 1) Mueve las articulaciones en control_joints.ipynb.
%      2) Copia aqui los 6 angulos (q_nb) y, si los da, x,y,z (xyz_nb).
%      3) Ejecuta (F5). Repite para cada pose.

clear; clc;

% ----------------------- DATOS DE ENTRADA (editar) -----------------------
q_nb   = [0 -30 30 0 30 0];   % angulos del notebook
unidad = 'deg';               % 'deg' o 'rad'
xyz_nb = [104.6 -40.3 393.3]; % [x y z] mm del notebook; [] si no lo da
% ------------------------------------------------------------------------

if strcmp(unidad,'deg'), q = deg2rad(q_nb); else, q = q_nb; end
[T, p] = fk_jetcobot(q);

disp('Matriz homogenea T (base -> efector):');
disp(round(T, 4));
fprintf('FK MATLAB:  x = %.1f   y = %.1f   z = %.1f  (mm)\n', p);

if ~isempty(xyz_nb)
    err = norm(p - xyz_nb);
    fprintf('Notebook :  x = %.1f   y = %.1f   z = %.1f  (mm)\n', xyz_nb);
    fprintf('Error de posicion = %.2f mm  ->  ', err);
    if err <= 10, disp('OK (<= 10 mm)'); else, disp('REVISAR (> 10 mm)'); end
end

% Referencia (grados, d6 = 53.7):  Cero (53.7,-63.4,412.7)   A (101.7,-36.5,397.9)
%   B (102.4,1.9,406.0)   C (149.3,-63.4,357.5)   D (66.8,15.1,411.1)

% ------------------------------ FUNCIONES --------------------------------
function [T, p] = fk_jetcobot(q)
% DH estandar. Fila: [theta_offset  d(mm)  a(mm)  alpha]
    DH = [  0      131.22    0      pi/2;
           -pi/2     0     -110.4   0;
            0        0      -96.0   0;
           -pi/2    63.4      0     pi/2;
            pi/2    75.05     0    -pi/2;
            0       53.7      0     0 ];   % d6 calibrado (45.6 + ~8 mm)
    T = eye(4);
    for i = 1:6
        th = q(i) + DH(i,1);  d = DH(i,2);  a = DH(i,3);  al = DH(i,4);
        ct = cos(th); st = sin(th); ca = cos(al); sa = sin(al);
        T = T * [ct, -st*ca,  st*sa, a*ct;
                 st,  ct*ca, -ct*sa, a*st;
                 0,      sa,     ca,    d;
                 0,       0,      0,    1];
    end
    p = T(1:3,4).';
end
