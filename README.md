# 📦 Sis_Estoque_Lotes - Sistema de Gestão de Estoque Inteligente

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-Framework-092E20?logo=django&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Database-4479A1?logo=mysql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?logo=bootstrap&logoColor=white)
![Gemini AI](https://img.shields.io/badge/AI-Google_Gemini-FF6F00?logo=google&logoColor=white)

Sistema de Gestão e Rastreabilidade de Estoque desenvolvido como Projeto de Estágio. O software tem como objetivo digitalizar o chão de fábrica, controlar o ciclo de vida de bobinas de aço e automatizar a entrada de dados utilizando Inteligência Artificial.

---

## 🚀 Principais Funcionalidades e Impactos

* **Backend Robusto:** Desenvolvido em Python com o framework Django, utilizando seu ORM para a gestão segura do estoque e validação de regras de negócio.
* **Integração com Inteligência Artificial:** Implementação da API do Google AI Studio (Gemini) para leitura e extração automatizada de dados em certificados MTC (PDFs).
* **Frontend Moderno e Ágil:** Interface de usuário formatada com o framework Bootstrap 5 para assegurar a padronização visual e a responsividade, integrada a requisições assíncronas (JavaScript) para buscas instantâneas no chão de fábrica.
* **Rastreabilidade Total:** Alcançado 100% de controle sobre o ciclo de vida das bobinas, incluindo o fracionamento dinâmico de lotes pesados e histórico detalhado de baixas.
* **Mitigação de Erros:** A automação via IA e as travas de validação no banco de dados (e na interface) reduziram drasticamente a margem de erro humano, como digitação incorreta ou notas duplicadas.
* **Ciclo de Melhoria Contínua:** Criação de um sistema de feedback nativo onde o operador reporta divergências, gerando dados para o refinamento futuro da Inteligência Artificial.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.12
* **Framework Web:** Django
* **Banco de Dados:** MySQL / MariaDB (Migrado do SQLite nativo para ambiente de produção)
* **Inteligência Artificial:** Google Generative AI (Modelo Gemini)
* **Frontend:** HTML5, CSS3, JavaScript e Bootstrap 5
* **Controle de Versão:** Git e GitHub

---

## ⚙️ Como executar o projeto localmente

### Pré-requisitos
* Python 3.12+ instalado
* Servidor MySQL (ex: XAMPP) rodando
* Git instalado

### Passo a Passo

1. **Clone o repositório:**
   git clone https://github.com/SEU_USUARIO/Sis_Estoque_Lotes.git
   cd Sis_Estoque_Lotes

2. **Crie e ative o ambiente virtual:**
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate

3. **Instale as dependências:**
   pip install -r requirements.txt

4. **Configuração de Variáveis de Ambiente (.env):**
   Crie um arquivo `.env` na raiz do projeto contendo as seguintes chaves:
   
   SECRET_KEY=sua_chave_secreta_do_django
   DEBUG=True
   DB_NAME=sis_estoque
   DB_USER=seu_usuario_mysql
   DB_PASSWORD=sua_senha_mysql
   DB_HOST=localhost
   DB_PORT=3306
   GEMINI_API_KEY=sua_chave_api_do_google

5. **Crie o banco de dados no MySQL:**
   Certifique-se de criar um banco chamado `sis_estoque` no seu SGBD (ex: phpMyAdmin ou MySQL Workbench).

6. **Execute as migrações:**
   python manage.py migrate

7. **Crie um superusuário (opcional):**
   python manage.py createsuperuser

8. **Inicie o servidor local:**
   python manage.py runserver
   
   Acesse o sistema no navegador através de: http://127.0.0.1:8000/

---

## 👨‍💻 Autor
**Gustavo** - *Desenvolvedor e Estagiário*