# Introduction 
System Awareness and Modelling for Response Analysis (SAMRA) is a method of analytical modelling that captures the behaviour of complex systems to forecast their behaviour under different scenarios and humanitarian responses. Unlike existing tools such as market maps, which capture mere snapshots of a system, SAMRA models capture the dynamic nature of complex systems by considering their evolution over time. SAMRA models reflect the underlying structure of the complex system, and are validated with expert assessment and against real-life data. Data from existing assessments, both qualitative and quantitative, is fed into SAMRA models to keep them updated, while also highlighting where primary data collection would be most valuable. SAMRA models can be used to predict outcomes for affected populations and private sector actors under hypothetical scenarios, as well as estimate the required humanitarian spending for different response options.

# Getting Started
1. Clone repo
2. Setup venv
3. Install requirements.txt
4. Setup database
   1. Create SQL database
   2. Modify `samra/settings.py` to connect to database
   3. Run `python manage.py makemigrations` and `python manage.py migrate`
5. Run with `python manage.py runserver`


# Build and Test
TODO: Describe and show how to build your code and run the tests. 

# Contribute
TODO: Explain how other users and developers can contribute to make your code better. 

If you want to learn more about creating good readme files then refer the following [guidelines](https://docs.microsoft.com/en-us/azure/devops/repos/git/create-a-readme?view=azure-devops). You can also seek inspiration from the below readme files:
- [ASP.NET Core](https://github.com/aspnet/Home)
- [Visual Studio Code](https://github.com/Microsoft/vscode)
- [Chakra Core](https://github.com/Microsoft/ChakraCore)