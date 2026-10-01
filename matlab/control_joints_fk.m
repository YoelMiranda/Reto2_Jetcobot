function control_joints_fk()
% CONTROL_JOINTS_FK  Interfaz para mover las 6 articulaciones y ver la FK.
%   Sliders en GRADOS (dentro de los limites del kit). Dibuja el brazo con los
%   frames DH 0..6 y muestra x,y,z del efector en mm.
%   Uso: mueve los MISMOS angulos en el robot (control_joints / send_angles)
%   y compara x,y,z con get_coords() o con una regla.
    lim = [-2.93 2.93; -2.36 2.36; -2.53 2.53; -2.58 2.58; -2.93 2.93; -3.14 3.14];
    limdeg = rad2deg(lim);
    f  = figure('Name','FK JetCobot','NumberTitle','off','Position',[100 80 1100 620]);
    ax = axes('Parent',f,'Position',[0.05 0.08 0.55 0.86]);
    txt = uicontrol(f,'Style','text','Units','normalized','Position',[0.63 0.83 0.35 0.13], ...
        'FontName','Consolas','FontSize',11,'HorizontalAlignment','left','BackgroundColor',f.Color);
    sl = gobjects(1,6);  ed = gobjects(1,6);
    for i = 1:6
        y = 0.72 - (i-1)*0.10;
        uicontrol(f,'Style','text','Units','normalized','Position',[0.63 y+0.035 0.06 0.04], ...
            'String',sprintf('q%d',i),'BackgroundColor',f.Color);
        sl(i) = uicontrol(f,'Style','slider','Units','normalized','Position',[0.69 y+0.035 0.21 0.04], ...
            'Min',limdeg(i,1),'Max',limdeg(i,2),'Value',0,'Callback',@(~,~)actualizar('slider'));
        ed(i) = uicontrol(f,'Style','edit','Units','normalized','Position',[0.91 y+0.035 0.07 0.04], ...
            'String','0','Callback',@(~,~)actualizar('edit'));
    end
    uicontrol(f,'Style','pushbutton','Units','normalized','Position',[0.63 0.08 0.15 0.06], ...
        'String','Pose cero','Callback',@(~,~)poner(zeros(1,6)));
    uicontrol(f,'Style','pushbutton','Units','normalized','Position',[0.80 0.08 0.15 0.06], ...
        'String','Pose ready','Callback',@(~,~)poner(rad2deg([0 -0.5 0.5 0 0.5 0])));
    actualizar('slider');

    function poner(qdeg)
        for k = 1:6, sl(k).Value = qdeg(k); end
        actualizar('slider');
    end

    function actualizar(origen)
        qdeg = zeros(1,6);
        for k = 1:6
            if strcmp(origen,'edit')
                v = str2double(ed(k).String);
                if isnan(v), v = sl(k).Value; end
                v = min(max(v, limdeg(k,1)), limdeg(k,2));
                sl(k).Value = v;
            end
            qdeg(k) = sl(k).Value;
            ed(k).String = sprintf('%.1f', qdeg(k));
        end
        q = deg2rad(qdeg);
        [T, p, Tac] = fk_jetcobot(q);
        cla(ax); hold(ax,'on'); grid(ax,'on'); axis(ax,'equal');
        P = squeeze(Tac(1:3,4,:)).';                       % 7x3 origenes de frames
        plot3(ax,P(:,1),P(:,2),P(:,3),'-o','LineWidth',3,'Color',[.2 .2 .2],'MarkerFaceColor','w');
        for k = 1:7                                        % ejes de cada frame
            o = Tac(1:3,4,k);  R = Tac(1:3,1:3,k);  s = 40;
            quiver3(ax,o(1),o(2),o(3),R(1,1)*s,R(2,1)*s,R(3,1)*s,'r','LineWidth',1.5);
            quiver3(ax,o(1),o(2),o(3),R(1,2)*s,R(2,2)*s,R(3,2)*s,'g','LineWidth',1.5);
            quiver3(ax,o(1),o(2),o(3),R(1,3)*s,R(2,3)*s,R(3,3)*s,'b','LineWidth',1.5);
            text(ax,o(1),o(2),o(3)+15,sprintf('%d',k-1));
        end
        plot3(ax,p(1),p(2),p(3),'m*','MarkerSize',12);
        xlabel(ax,'X (mm)'); ylabel(ax,'Y (mm)'); zlabel(ax,'Z (mm)');
        axis(ax,[-500 500 -500 500 0 550]); view(ax,135,25);
        txt.String = sprintf(['q (deg): %s\n\nFK  x = %8.1f mm\n    y = %8.1f mm\n    z = %8.1f mm\n' ...
            '|p| = %8.1f mm'], mat2str(round(qdeg,1)), p(1), p(2), p(3), norm(p));
    end
end
