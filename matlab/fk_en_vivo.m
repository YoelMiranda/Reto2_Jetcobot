function fk_en_vivo(dominio)
% FK_EN_VIVO  Escucha /joint_states (ROS 2, ROS Toolbox) e imprime la FK.
%   Sirve para mover el brazo con control_joints y ver a la vez la FK de MATLAB.
%   Requiere ROS Toolbox y el mismo ROS_DOMAIN_ID (42 + n de equipo).
%   Solo SUSCRIBE; NO publica nada (regla de oro del reto).
%   Uso:  fk_en_vivo(45)    % Ctrl+C para terminar
    if nargin < 1, dominio = str2double(getenv('ROS_DOMAIN_ID')); end
    nodo = ros2node('/fk_matlab', dominio);
    nombres = {'1_Joint','2_Joint','3_Joint','4_Joint','5_Joint','6_Joint'};
    sub = ros2subscriber(nodo,'/joint_states','sensor_msgs/JointState');
    disp('Escuchando /joint_states ... Ctrl+C para salir');
    while true
        msg = receive(sub, 5);
        n = string(msg.name);  pos = double(msg.position);
        q = zeros(1,6);
        for k = 1:6
            idx = find(n == nombres{k}, 1);
            if isempty(idx), q(k) = pos(k); else, q(k) = pos(idx); end
        end
        [~, p] = fk_jetcobot(q);
        fprintf('q(deg)=%s  ->  x=%7.1f  y=%7.1f  z=%7.1f mm\n', mat2str(round(rad2deg(q),1)), p);
        pause(0.2);
    end
end
