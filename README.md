## UP Scholarship
Automate filling of UP Scholarship forms.
## Requirements
- Python >= 3.7
- [MS Build Tools v142](https://www.visualstudio.com/downloads/#build-tools-for-visual-studio-2019) 
## Installation
Install using `pip install git+https://github.com/meashishsaini/up_scholarship`
## Usage
```
up_scholarship [-h] [--filepath FILEPATH]
                      {register,filldata,uploadphoto,submitcheck,renew,submitfinal,receive,verify,forward,aadhaarauth,savecaptchas,scanphoto,convert2pdf,printfinal,donestudent}

positional arguments:
  {register,filldata,uploadphoto,submitcheck,renew,submitfinal,receive,verify,forward,aadhaarauth,savecaptchas,scanphoto,convert2pdf,printfinal,donestudent}
                        tell which spider needed to be run.

optional arguments:
  -h, --help            show this help message and exit
  --filepath FILEPATH, -f FILEPATH
                        path of input file
```