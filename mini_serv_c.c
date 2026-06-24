#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <netinet/ip.h>

int		count, max_fd;
int		ids[65536];
char	*msgs[65536];
fd_set	afds, rfds, wfds;
char	buf[1001], out[64];

int	extract_message(char **buf, char **msg)
{
	char	*newbuf;
	int		i;

	*msg = 0;
	if (!*buf)
		return (0);
	i = 0;
	while ((*buf)[i])
	{
		if ((*buf)[i] == '\n')
		{
			newbuf = calloc(strlen(*buf + i + 1) + 1, 1);
			if (!newbuf)
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

char	*str_join(char *buf, char *add)
{
	char	*newbuf;
	int		len;

	len = buf ? strlen(buf) : 0;
	newbuf = malloc(len + strlen(add) + 1);
	if (!newbuf)
		return (0);
	newbuf[0] = 0;
	if (buf)
		strcat(newbuf, buf);
	free(buf);
	strcat(newbuf, add);
	return (newbuf);
}

void	die(void)
{
	write(2, "Fatal error\n", 12);
	exit(1);
}

void	send_all(int except, char *s)
{
	for (int fd = 0; fd <= max_fd; fd++)
		if (FD_ISSET(fd, &wfds) && fd != except)
			send(fd, s, strlen(s), 0);
}

int	main(int ac, char **av)
{
	if (ac != 2)
	{
		write(2, "Wrong number of arguments\n", 26);
		exit(1);
	}

	FD_ZERO(&afds);
	int sockfd = socket(AF_INET, SOCK_STREAM, 0);
	if (sockfd < 0)
		die();
	max_fd = sockfd;
	FD_SET(sockfd, &afds);

	struct sockaddr_in sa;
	bzero(&sa, sizeof(sa));
	sa.sin_family = AF_INET;
	sa.sin_addr.s_addr = htonl(2130706433);
	sa.sin_port = htons(atoi(av[1]));

	if (bind(sockfd, (struct sockaddr *)&sa, sizeof(sa)))
		die();
	if (listen(sockfd, 128))
		die();

	while (1)
	{
		rfds = wfds = afds;
		if (select(max_fd + 1, &rfds, &wfds, NULL, NULL) < 0)
			die();

		for (int fd = 0; fd <= max_fd; fd++)
		{
			if (!FD_ISSET(fd, &rfds))
				continue;

			if (fd == sockfd)
			{
				int cfd = accept(sockfd, NULL, NULL);
				if (cfd < 0)
					continue;
				if (cfd > max_fd)
					max_fd = cfd;
				ids[cfd] = count++;
				msgs[cfd] = NULL;
				FD_SET(cfd, &afds);
				sprintf(out, "server: client %d just arrived\n", ids[cfd]);
				send_all(cfd, out);
				break;
			}
			else
			{
				int n = recv(fd, buf, 1000, 0);
				if (n <= 0)
				{
					sprintf(out, "server: client %d just left\n", ids[fd]);
					send_all(fd, out);
					free(msgs[fd]);
					FD_CLR(fd, &afds);
					close(fd);
					break;
				}
				buf[n] = 0;
				if (!(msgs[fd] = str_join(msgs[fd], buf)))
					die();
				char *msg;
				while (extract_message(&msgs[fd], &msg))
				{
					sprintf(out, "client %d: ", ids[fd]);
					send_all(fd, out);
					send_all(fd, msg);
					free(msg);
				}
			}
		}
	}
	return (0);
}