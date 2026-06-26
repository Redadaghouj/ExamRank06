#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <netinet/ip.h>

int		g_count, g_maxfd, g_ids[65536];
char	*g_msgs[65536], g_buf[1001], g_out[64];
fd_set	g_afds, g_rfds, g_wfds;

int	extract_message(char **buf, char **msg)
{
	char	*nl;
	char	*n;

	*msg = 0;
	if (!*buf || !(nl = strstr(*buf, "\n")))
		return (0);
	n = calloc(strlen(nl + 1) + 1, 1);
	if (!n)
		return (-1);
	strcpy(n, nl + 1);
	*msg = *buf;
	*(nl + 1) = 0;
	*buf = n;
	return (1);
}

char	*str_join(char *buf, char *add)
{
	int		len = buf ? strlen(buf) : 0;
	char	*n = malloc(len + strlen(add) + 1);

	if (!n)
		return (0);
	n[0] = 0;
	if (buf)
		strcat(n, buf);
	free(buf);
	return (strcat(n, add));
}

void	die(void) { write(2, "Fatal error\n", 12); exit(1); }

void	send_all(int skip, char *s)
{
	for (int fd = 0; fd <= g_maxfd; fd++)
		if (fd != skip && FD_ISSET(fd, &g_wfds))
			send(fd, s, strlen(s), MSG_NOSIGNAL);
}

void	handle_connect(int sock)
{
	int	cfd;

	cfd = accept(sock, NULL, NULL);
	if (cfd < 0)
		return ;
	if (cfd > g_maxfd)
		g_maxfd = cfd;
	g_ids[cfd] = g_count++;
	g_msgs[cfd] = NULL;
	FD_SET(cfd, &g_afds);
	sprintf(g_out, "server: client %d just arrived\n", g_ids[cfd]);
	send_all(cfd, g_out);
}

void	handle_disconnect(int fd)
{
	sprintf(g_out, "server: client %d just left\n", g_ids[fd]);
	send_all(fd, g_out);
	free(g_msgs[fd]);
	g_msgs[fd] = NULL;
	FD_CLR(fd, &g_afds);
	close(fd);
}

void	handle_recv(int fd)
{
	char	*msg;
	int		n;

	n = recv(fd, g_buf, 1000, 0);
	if (n <= 0)
	{
		handle_disconnect(fd);
		return ;
	}
	g_buf[n] = 0;
	if (!(g_msgs[fd] = str_join(g_msgs[fd], g_buf)))
		die();
	while (extract_message(&g_msgs[fd], &msg))
	{
		sprintf(g_out, "client %d: ", g_ids[fd]);
		send_all(fd, g_out);
		send_all(fd, msg);
		free(msg);
	}
}

int	main(int ac, char **av)
{
	if (ac != 2) { write(2, "Wrong number of arguments\n", 26); exit(1); }

	int sock = socket(AF_INET, SOCK_STREAM, 0);
	if (sock < 0)
		die();
	FD_ZERO(&g_afds);
	g_maxfd = sock;
	FD_SET(sock, &g_afds);

	struct sockaddr_in sa = {.sin_family = AF_INET,
		.sin_port = htons(atoi(av[1])), .sin_addr.s_addr = htonl(2130706433)};
	if (bind(sock, (struct sockaddr *)&sa, sizeof(sa)) || listen(sock, 128))
		die();

	while (1)
	{
		g_rfds = g_wfds = g_afds;
		if (select(g_maxfd + 1, &g_rfds, &g_wfds, NULL, NULL) < 0)
			die();
		for (int fd = 0; fd <= g_maxfd; fd++)
		{
			if (!FD_ISSET(fd, &g_rfds))
				continue ;
			if (fd == sock)
				handle_connect(sock);
			else
				handle_recv(fd);
		}
	}
	return (0);
}