% PRUEBA_FK  Compara fk_jetcobot (DH calibrada, d6 = 53.7) contra lo medido en el
% robot para las 5 poses de verificacion del RB-2 (angulos en GRADOS).
%   Requiere fk_jetcobot.m y dh_jetcobot.m en la misma carpeta.
nombres = {'Cero','A','B','C','D'};
q_deg = [ 0   0  0  0  0 0;
          0 -30 30  0 30 0;
         30 -20 20  0 15 0;
          0 -60 60  0  0 0;
         45 -30 30 30 30 0];
medido = [ 52.6 -64.7 409.2;      % x y z (mm) medidos en el robot
          104.6 -40.3 393.3;
          105.7  -1.1 401.5;
          152.5 -62.0 351.3;
           71.3  13.3 406.4];
esperado = [ 53.7 -63.4 412.7;    % FK esperada (calculo independiente en Python)
            101.7 -36.5 397.9;
            102.4   1.9 406.0;
            149.3 -63.4 357.5;
             66.8  15.1 411.1];
fprintf('%-5s %-24s %-24s %9s %10s\n','pose','FK MATLAB (x,y,z)','medido (x,y,z)','error mm','MATLAB-Py');
err = zeros(5,1);
for k = 1:5
    [~, p] = fk_jetcobot(deg2rad(q_deg(k,:)));
    err(k) = norm(p - medido(k,:));
    fprintf('%-5s (%6.1f,%6.1f,%6.1f)  (%6.1f,%6.1f,%6.1f)  %8.1f  %9.3f\n', ...
        nombres{k}, p, medido(k,:), err(k), norm(p - esperado(k,:)));
end
fprintf('\nError medio %.1f mm, maximo %.1f mm (criterio <= 10 mm)\n', mean(err), max(err));
