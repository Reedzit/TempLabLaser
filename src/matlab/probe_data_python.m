%Thomas Andrews
%Adapted from "light_data_intake" by David Leavitt
%05SEP23
%TEMP Lab
%Code to intake raw I and Q data, subtract noise, and plot phase and 
%amplitude. 
% Ensure data being saved from LIC is labeled "d" for data frames and "n" 
% for noise frames, with ONLY .txt files from the LIC in the folder.
%function [figure1data, figure2data, figure3data, figure4dataA, figure4dataB] = probe_data_python()
function [figure1data, figure2data, figure3data] = probe_data_python()

clear all;

%% Run this step if loading a new file set
% Determine number of files (frames) of each quadratrure in folder
txtFiles = dir('testData\*.txt'); % changed to go to a separate folder for test files
numfiles = length(txtFiles);
mydata = cell(1, numfiles);
setFrame = numfiles/4;

%% Run from this step if the file set is unchanged
% Import data into cell in order of dI, dQ, nI, nQ
for k = 1:numfiles 
  mydata{k} = importdata(strcat('testData\',txtFiles(k).name)); % changed to go to test files to import the data.
end

%Evaluate noise and average.
noise=zeros(setFrame,300,300);
for k=1:setFrame
    noise(k,:,:)=mydata{k+2*setFrame}+1i*mydata{k+3*setFrame};
end
nmean=sum(noise)/setFrame;

%Correct I and Q data, then find amplitude and phase
%[x,y]=dim(Im);
data=zeros(setFrame,300,300);
for k=1:setFrame
    data(k,:,:)=mydata{k}+1i*mydata{k+setFrame};
end
%% Run from here if you are only changing the signal processing chain
look=0;
if look==0
    corrected=squeeze(sum(data)/setFrame-nmean);%
else 
    corrected=squeeze(data(look,:,:)-nmean);%
end
xband=corrected(:,[50:80,220:250]);
yband=corrected([50:80,220:250],:);
xwave=mean(xband, 2);
ywave=mean(yband, 1);
wave=xwave*ywave;
calm=corrected-wave;
corrected=corrected.*exp(1i*pi);%adjust phase by a constant offset
% Cut out edges with data jumps
% for k = 1:300
%     for j = 1:300
%         if j <= 10 || 290 <= j       
%             corrected(k,j) = NaN;
%         end
%     end
%     if k <= 10 || 290 <= k          
%         corrected(k,j) = NaN;
%     end
% end
% Filters out regions where the amplitude is too small to get a clean
%signal
%thresh=5;
% for k=1:300
%     for l=1:300        
%         if abs(corrected(k,l))<thresh
%             corrected(k,l)=nan;
%         end
%     end
% end
% Filters for full cycle phase shifts. May help see the rolloff
Edge=zeros(298,298);
test=[0,0,0,0];
for k=2:299
    for l=2:299
        test(1)=fix((corrected(k,l)-corrected(k-1,l))/pi);
        test(2)=fix((corrected(k,l)-corrected(k,l-1))/pi);
        test(3)=fix((corrected(k,l)-corrected(k+1,l))/pi);
        test(4)=fix((corrected(k,l)-corrected(k,l+1))/pi);
        if test==[0,0,0,0]
            Edge(k-1,l-1)=1;
        end
        test=[0,0,0,0];
    end
end
A=fft2(angle(corrected));
for k=-149:150
    for l=-149:150        
        if abs(k+1i*l)>=150
            A(k+150,l+150)=0;
        end
    end
end
ang=ifft2(A);
%figure(4)
%surf(real(ang))

% Smooth data (can be changed if needed, or put to 1 for no smoothing).
% Larger x denotes wider smoothing chunks (2-3 is about good).
% Smoothing value should be less than the thermal wavelength
x = 5;
m = (1/(x^2)) * ones(x);
corrected = conv2(corrected,m,"same");
[~,ind]=max(abs(corrected),[],'all','linear');
center=[floor(ind/300),mod(ind,300)];
zoom=7;
interest=corrected(max([center(2)-zoom,1]):min([center(2)+zoom,300]),max([center(1)-zoom,1]):min([center(1)+zoom,300]));
%% Plot results


% Plot phase on surface
a = figure(1); clf
figure1data = angle(corrected(1:300,1:300));
% a.WindowState = 'maximized';
surf(angle(corrected(1:300,1:300)));

% Plot amplitude on surface
b = figure(2); clf
figure2data = abs(corrected(1:300,1:300));
% b.WindowState = 'maximized';
surf(abs(corrected(1:300,1:300)));

%Plot phase jumps on surface
c=figure(3); clf
figure3data = unwrap_phase(angle(interest));
surf(unwrap_phase(angle(interest)));

%%
% d=figure(4); clf
% figure4dataA = unwrap(angle(corrected(center(2),max([center(1)-zoom,1]):min([center(1)+zoom,300]))));
% 
% %debug
% % figure4dataB = max([center(2)-zoom,1]):min([center(2)+zoom,300]);
% % figure4dataB = unwrap(angle(corrected(max([center(2)-zoom,1]):min([center(2)+zoom,300]),center(1))));
% figure4dataB = unwrap(angle(corrected(max([center(2)-zoom,1]):min([center(2)+zoom,300]),center(1))));
% 
% plot(unwrap(angle(corrected(center(2),max([center(1)-zoom,1]):min([center(1)+zoom,300])))));
% hold on
% plot(unwrap(angle(corrected(max([center(2)-zoom,1]):min([center(2)+zoom,300]),center(1)))));
% hold off

end