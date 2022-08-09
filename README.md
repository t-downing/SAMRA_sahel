# SAMRA web app

## Introduction 
System Awareness and Modelling for Response Analysis (SAMRA) is a method of analytical modelling that captures the behaviour of complex systems to forecast their behaviour under different scenarios and humanitarian responses. Unlike existing tools such as market maps, which capture mere snapshots of a system, SAMRA models capture the dynamic nature of complex systems by considering their evolution over time. SAMRA models reflect the underlying structure of the complex system, and are validated with expert assessment and against real-life data. Data from existing assessments, both qualitative and quantitative, is fed into SAMRA models to keep them updated, while also highlighting where primary data collection would be most valuable. SAMRA models can be used to predict outcomes for affected populations and private sector actors under hypothetical scenarios, as well as estimate the required humanitarian spending for different response options.

## Getting Started
1. Clone repo
2. Setup venv
3. Install requirements.txt
4. Setup database
   1. Create SQL database
   2. Modify `samra/settings.py` to connect to database
   3. Run `python manage.py makemigrations` and `python manage.py migrate`
5. Run with `python manage.py runserver`

## Current Issues
- the version of `dash-bootstrap-components` used is technically not compatible with `django-plotly-dash`
- there are a few packages that appear to be only required for windows (`pywin32`, `pywinpty`, and `twisted-iocpsupport`)
- the line `from .sd_model import ...` in `sahel/views.py` needs to be commented out when running `python manage.py makemigrations`
