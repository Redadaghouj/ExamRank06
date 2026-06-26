#include <string.h>
#include <unistd.h>
#include <netdb.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <stdio.h>

#define WRONG_AC "Wrong number of arguments\n"
#define ERROR "Fatal error\n"

int		g_count, g_maxfd, g_ids[65536];
char	*g_msgs[65536], g_buf[1001], g_out[64];
fd_set	g_afds, g_rfds, g_wfds;

int extract_message(char **buf, char **msg)
{
	char    *newbuf;
	int     i;

	*msg = 0;
	if (*buf == 0)
		return (0);
	i = 0;
	while ((*buf)[i])
	{
		if ((*buf)[i] == '\n')
		{
			newbuf = calloc(1, sizeof(*newbuf) * (strlen(*buf + i + 1) + 1));
			if (newbuf == 0)
				return (-1);
			strcpy(newbuf, *buf + i + 1);
			*msg = *buf;
			(*msg)[i + 1] = 0;
			*buf = newbuf;
			return (1);
		}
		i++;
	}
	return (0);
}

char *str_join(char *buf, char *add)
{
	char    *newbuf;
	int     len;

	if (buf == 0)
		len = 0;
	else
		len = strlen(buf);
	newbuf = malloc(sizeof(*newbuf) * (len + strlen(add) + 1));
	if (newbuf == 0)
		return (0);
	newbuf[0] = 0;
	if (buf != 0)
		strcat(newbuf, buf);
	free(buf);
	strcat(newbuf, add);
	return (newbuf);
}

void	die(char* s)
{
	write(2, s, strlen(s));
	exit(1);
}

void	send_all(int skip, char *s)
{
	for (int fd = 0; fd <= g_maxfd; fd++)
		if (fd != skip && FD_ISSET(fd, &g_wfds))
			send(fd, s, strlen(s), MSG_NOSIGNAL);
}

void	handle_new_client(int sockfd)
{
	int	connfd = accept(sockfd, NULL, NULL);

	if (connfd < 0)
		return ;
	if (connfd > g_maxfd)
		g_maxfd = connfd;
	g_ids[connfd] = g_count++;
	g_msgs[connfd] = NULL;
	FD_SET(connfd, &g_afds);
	sprintf(g_out, "server: client %d just arrived\n", g_ids[connfd]);
	send_all(connfd, g_out);
}

void	handle_client_gone(int fd)
{
	sprintf(g_out, "server: client %d just left\n", g_ids[fd]);
	send_all(fd, g_out);
	free(g_msgs[fd]);
	g_msgs[fd] = NULL;
	FD_CLR(fd, &g_afds);
	close(fd);
}

void	handle_client_msg(int fd)
{
	int		n = recv(fd, g_buf, 1000, 0);
	char	*msg;

	if (n <= 0)
	{
		handle_client_gone(fd);
		return ;
	}
	g_buf[n] = 0;
	if (!(g_msgs[fd] = str_join(g_msgs[fd], g_buf)))
		die(ERROR);
	while (extract_message(&g_msgs[fd], &msg))
	{
		sprintf(g_out, "client %d: ", g_ids[fd]);
		send_all(fd, g_out);
		send_all(fd, msg);
		free(msg);
	}
}

int main(int ac, char **av)
{
	if (ac != 2)
		die(WRONG_AC);

	int sockfd = socket(AF_INET, SOCK_STREAM, 0);
	if (sockfd < 0)
		die(ERROR);

	struct sockaddr_in servaddr;
	bzero(&servaddr, sizeof(servaddr));
	servaddr.sin_family = AF_INET;
	servaddr.sin_addr.s_addr = htonl(2130706433);
	servaddr.sin_port = htons(atoi(av[1]));

	if (bind(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr)) != 0)
		die(ERROR);
	if (listen(sockfd, 10) != 0)
		die(ERROR);

	FD_ZERO(&g_afds);
	FD_SET(sockfd, &g_afds);
	g_maxfd = sockfd;

	while (1)
	{
		g_rfds = g_wfds = g_afds;
		if (select(g_maxfd + 1, &g_rfds, &g_wfds, NULL, NULL) < 0)
			die(ERROR);
		for (int fd = 0; fd <= g_maxfd; fd++)
		{
			if (!FD_ISSET(fd, &g_rfds))
				continue ;
			if (fd == sockfd)
			{
				handle_new_client(sockfd);
				break ;
			}
			handle_client_msg(fd);
		}
	}
	return (0);
}