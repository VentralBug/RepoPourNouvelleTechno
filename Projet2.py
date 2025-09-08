# -----------------------------------------------------------------------------
# Script : Projet.py
# Auteur : Samuel Pomerleau
# Description : Permet de prendre des mesures sur des ordinateurs avec une connnection SSH
# Paramètres : AUCUN
# Date : 2025-03-12
# -----------------------------------------------------------------------------

import paramiko
import pandas as pd
import datetime

# --------------------------------------------------------------------------- Def

def ssh_connect(hostname:str, username:str, password:str):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=hostname, username=username, password=password)
        return client
    except:
        return None


def run_windows_commands(client, df, index):
    os_version_command = 'powershell "(Gt-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption)'
    cpu_usage_command = 'powershell "(Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"'
    ram_command = 'powershell "(Get-WmiObject Win32_OperatingSystem).TotalVisibleMemorySize / 1MB - (Get-WmiObject Win32_OperatingSystem).FreePhysicalMemory / 1MB | ForEach-Object { \\"{0:N2} / {1:N2} Go\\" -f $_, ((Get-WmiObject Win32_OperatingSystem).TotalVisibleMemorySize / 1MB) }"'
    disk_command = 'powershell "Get-PSDrive -PSProvider FileSystem | ForEach-Object {Write-Output \\"$($_.Name): $([math]::round($_.Used / 1GB, 2)) / $([math]::round(($_.Used + $_.Free) / 1GB, 2)) go\\"}"'
    user_list_command = 'powershell "(Get-LocalUser | ForEach-Object { $_.Name }) -join \\",\\""'
    list_file_command = 'ls c:\\'


    output = ssh_command(client, os_version_command)
    output =  output.replace('\r\n','')
    df.loc[index, "Version OS"] = output

    output = ssh_command(client, cpu_usage_command)
    output = output.replace('\r\n', '')
    df.loc[index, "Charge CPU"] = output

    output = ssh_command(client, ram_command)
    output = output.replace('\r\n', '')
    df.loc[index, "RAM Disponible"] = output

    output = ssh_command(client, disk_command)
    output = output.replace('\r\n', ',')
    output = output.rstrip(',')
    df.loc[index, "Espace disque disponible"] = output

    output = ssh_command(client, user_list_command)
    output = output.replace('\r\n', '')
    df.loc[index, "Utilisateurs"] = output

    output = ssh_command(client, list_file_command)
    output = output.replace('\r\n', '')
    df.loc[index, "Fichier"] = output


    return df


def run_linux_commands(client, df, index):
    os_version_command = 'lsb_release -d | cut -f2-'
    cpu_usage_command = "echo $[100-$(vmstat 1 2|tail -1|awk '{print $15}')]"
    ram_command = 'free | grep Mem | awk \'{printf "%.2f / %.2f Go\\n", $3/1024/1024, $2/1024/1024}\''
    disk_command = 'daf -h --output=source,used,size | grep -v tmpfs | tail -n +2 | awk \'{print $1 \" \" $2 \"/\" $3 \"Go\"}\''
    user_list_command = "getent passwd | cut -d: -f1 | tr '\n' ',' "
    list_file_commande = "ls /"

    output = ssh_command(client, os_version_command)
    output = output.replace('\n', '')
    df.loc[index,"Version OS"] = output

    output = ssh_command(client, cpu_usage_command)
    output = output.replace('\n', '')
    df.loc[index,"Charge CPU"] = output

    output = ssh_command(client, ram_command)
    output = output.replace('\n', '')
    df.loc[index,"RAM Disponible"] = output

    output = ssh_command(client, disk_command)
    output = output.replace('\n', '|')
    output = output.rstrip('|')
    df.loc[index, "Espace disque disponible"] = output

    output = ssh_command(client, user_list_command)
    output = output.rstrip(',')
    df.loc[index,"Utilisateurs"] = output

    output = ssh_command(client, list_file_commande)
    output = output.rstrip(',')
    df.loc[index,"Fichiers à la racine"] = output

    return df


def ssh_command(client:paramiko.SSHClient(), command:str):
    stdin, stdout, stderr = client.exec_command(command)
    output = str(stdout.read().decode())
    error = str(stderr.read().decode())
    if output:
        return output
    else:
        return error

def ssh_close(client:paramiko.SSHClient()):
    client.close()


def print_infos(df,index):
    disk_list = []

    if df.loc[index, "Type système"] == "Windows":
        for disk in df.loc[index, "Espace disque disponible"].rsplit(','):
            disk_list.append(f"{disk}")
    else:
        for disk in df.loc[index, "Espace disque disponible"].rsplit('|'):
            disk_list.append(f"{disk}")

    infos = [f"Version OS : {df.loc[index,"Version OS"]}",
             f"Charge CPU : {df.loc[index,"Charge CPU"]}%",
             f"RAM Disponible : {df.loc[index, "RAM Disponible"]}",
             f"Espace disponible: {'\nEspace disponible: '.join(disk_list)}",
             f"Liste utilisateurs : {df.loc[index,"Utilisateurs"]}"]

    for info in infos:
        print(info)
        append_logfile(info)

def print_error(message):
    print(f"\033[31m{message}\033[0m")


def read_file(file_path):
    dataframe = pd.read_csv(file_path, encoding="utf-8", sep=",")
    return dataframe


def append_logfile(string):
    date = datetime.datetime.now()
    with open("logs.log","a", encoding = "UTF-8") as file:
        file.write(f"{date}\t{string}\n")
    file.close()


# --------------------------------------------------------------------------- Main

df_ordinateurs = pd.read_csv("machines.csv")

df_ordinateurs["Version OS"] = ""
df_ordinateurs["Charge CPU"] = ""
df_ordinateurs["RAM Disponible"] = ""
df_ordinateurs["Espace disque disponible"] = ""
df_ordinateurs["Utilisateurs"] = ""
df_ordinateurs["Fichiers à la racine"] = ""


for index, row in df_ordinateurs.iterrows():

    client = ssh_connect(row["Adresse IP"], row["user"], row["mdp"])
    append_logfile(f"{25 * '*'} Connection à {row["Type système"]} : {row["Adresse IP"]}...")
    print(f"{25 * '*'} Connection à {row["Type système"]} : {row["Adresse IP"]}...")

    if client is not None:
        if row["Type système"] == "Windows":
            df_ordinateurs = run_windows_commands(client, df_ordinateurs, index)
        elif row["Type système"] == "Linux":
            df_ordinateurs = run_linux_commands(client, df_ordinateurs, index)
        else:
            result = None

        # print_infos(df_ordinateurs,index)

        ssh_close(client)
    else:
        # print_error(f"Impossible d'établir une connection vers la machine {row["Adresse IP"]}")
        append_logfile(f"Impossible d'établir une connection vers la machine {row["Adresse IP"]}")

    df_results = df_ordinateurs

    df_results.to_csv("results.csv", index=False)
